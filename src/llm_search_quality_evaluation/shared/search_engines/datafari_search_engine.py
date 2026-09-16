from pathlib import Path
import requests
from pydantic import HttpUrl
from requests.exceptions import RequestException
from typing import List, Dict, Any, Union
from llm_search_quality_evaluation.shared.search_engines.search_engine_base import BaseSearchEngine
from llm_search_quality_evaluation.shared.search_engines.solr_search_engine import SolrSearchEngine
from llm_search_quality_evaluation.shared.models.document import Document
from llm_search_quality_evaluation.shared.utils import clean_text

import logging
import json

log = logging.getLogger(__name__)

"""
Datafari search-engine implementation.

Datafari exposes a Solr-compatible search API, but expects the collection
name as a request parameter rather than as part of the endpoint URL.
"""


class DatafariSearchEngine(BaseSearchEngine):
    """
    Datafari implementation to search into a given collection
    """

    DEFAULT_TIMEOUT = 30

    def __init__(self, endpoint: HttpUrl, collection_name: str):
        super().__init__(endpoint)
        self.collection_name = collection_name
        self.HEADERS = {"Accept": "application/json"}
        self.UNIQUE_KEY = "id"  # forcing the unique key to be 'id'
        log.debug(f"Working on endpoint: {self.endpoint}")

    @property
    def _fetch_all_payload(self) -> Dict[str, Any]:
        return {
            "q": "*:*",
        }

    def _get_total_hits(self, payload: Dict[str, Any]) -> int:
        search_url = self.endpoint.encoded_string().rstrip("/")
        payload = payload.copy()

        # Force datafari to return a JSON formatted response
        payload["wt"] = "json"
        if self.collection_name:
            payload["collection"] = self.collection_name

        log.debug("Retrieving all docs to count them")
        log.debug(f"Search url: {search_url}")
        log.debug(
            f"datafari payload (showing payload 500 first chars): {str(payload)[:500]}"
        )

        try:
            response = requests.get(search_url, headers=self.HEADERS, params=payload, timeout=self.DEFAULT_TIMEOUT)
            response.raise_for_status()
        except (RequestException) as e:
            log.error(f"Datafari query failed: {e}\n")
            raise

        return int(response.json().get("response", {}).get("numFound", 0))


    def fetch_for_query_generation(
        self,
        documents_filter: Union[None, List[Dict[str, List[str]]]],
        number_of_docs: int,
        doc_fields: List[str],
        start: int = 0
    ) -> List[Document]:
        """
        Fetches a set of documents from datafari for the purpose of query generation.

        Args:
            documents_filter (Union[None, List[Dict[str, List[str]]]]): Optional filter constraints for fields and their allowed values.
            number_of_docs (int): Number of documents to retrieve.
            doc_fields (List[str]): List of field names to include in the output.
            start (int, optional): Starting index of the query. Defaults to 0.
        Returns:
            List[Document]: A list of retrieved documents as `Document` objects.
        """
        log.debug(
            f"Fetching {number_of_docs} documents (rows) from the search engine for query generation"
        )

        payload: Dict[str, Any] = self._fetch_all_payload
        payload["rows"] = number_of_docs
        payload["start"] = start
        payload["fl"] = self._format_fields(doc_fields)
        payload["collection"] = self.collection_name
        if documents_filter is not None:
            payload["fq"] = []
            for dict_field in documents_filter:
                for field, values in dict_field.items():
                    if not values:
                        continue  # skip empty lists
                    if len(values) == 1:
                        clause = f"{field}:{values[0]}"
                    else:
                        or_values = " OR ".join(f"{v}" for v in values)
                        clause = f"{field}:({or_values})"
                    payload["fq"].append(clause)

        return self._search(payload)

    def fetch_for_evaluation(
        self,
        query_template: Path | str,
        doc_fields: List[str],
        keyword: str = "*:*",
        extra_placeholders: Dict[str, str] | None = None,
    ) -> List[Document]:
        """
        Executes a search using a query template for evaluation purposes.

        Args:
            query_template (Path): Path variable pointing to the file with the payload a placeholder for the keyword.
            doc_fields (List[str]): List of fields to include in the response.
            keyword (str, optional): Keyword to inject into the query template. Defaults to "*:*".

        Returns:
            List[Document]: A list of documents matching the query.
        """
        log.info(
            "Fetching documents (rows) based on query template for query evaluation"
        )

        query_template = Path(query_template)
        payload: Dict[str, Any] = self._parse_query_template(
            query_template, extra_placeholders
        )
        payload = self._replace_placeholder(
            payload, self.QUERY_PLACEHOLDER, self.escape(keyword)
        )
        payload["fl"] = self._format_fields(doc_fields)
        payload["collection"] = self.collection_name

        return self._search(payload)

    def fetch_field_values(self, values_query_template: Path | str, field: str) -> List[str]:
        """Run a Solr-style facet template through the Datafari endpoint."""
        payload = self._parse_query_template(values_query_template)
        payload["wt"] = "json"
        payload["collection"] = self.collection_name
        try:
            response = requests.get(
                self.endpoint.encoded_string().rstrip("/"),
                headers=self.HEADERS,
                params=payload,
                timeout=self.DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            body = response.json()
        except RequestException as e:
            log.error("Datafari value-discovery query failed: %s", e)
            raise

        try:
            return SolrSearchEngine._list_values_from_facet_fields(body, field)
        except ValueError as e:
            raise ValueError(f"Datafari value-discovery: {e}") from e

    def _search(self, payload: Dict[str, Any],) -> List[Document]:
        """
        Executes a datafari search using a JSON payload and parses the results.

        Args:
            payload (Dict[str, Any]): Query parameters sent with the Datafari GET request.

        Returns:
            List[Document]: A list of documents formatted as `Document` instances.
        """

        payload = payload.copy()
        search_url = self.endpoint.encoded_string().rstrip("/")

        # Force datafari to return a JSON formatted response
        payload["wt"] = "json"

        log.info(f"Search url: {search_url}")
        log.debug(
            f"datafari payload (showing payload 500 first chars): {str(payload)[:500]}"
        )

        try:
            response = requests.get(search_url, headers=self.HEADERS, params=payload, timeout=self.DEFAULT_TIMEOUT)
            log.debug("Request URL: %s", response.request.url)
            response.raise_for_status()
        except (RequestException) as e:
            log.error(f"Datafari query failed: {e}\n")
            raise

        body = response.json()
        if not isinstance(body, dict) or not isinstance(body.get("response"), dict):
            raise ValueError("Datafari search: expected a JSON object containing a response object")
        hits = body["response"].get("docs")
        if not isinstance(hits, list) or any(not isinstance(hit, dict) for hit in hits):
            raise ValueError("Datafari search: expected response.docs to be a list of document objects")
        result = []
        for hit in hits:
            doc_id = hit.get(self.UNIQUE_KEY)
            fields = {
                key: self._normalize(value)
                for key, value in hit.items()
                if key != self.UNIQUE_KEY
            }
            result.append(Document(id=doc_id, fields=fields))
        log.info(f"Fetched {len(result)} documents from the engine")
        return result

    def _format_fields(self, doc_fields: List[str]) -> str:
        fields = list(doc_fields)

        if self.UNIQUE_KEY not in fields:
            fields.append(self.UNIQUE_KEY)

        return ",".join(fields)

    @staticmethod
    def _normalize(value: Any) -> List[str]:
        """Normalize a field value into a list of cleaned strings or throws an exception."""
        try:
            if value is None:
                return []

            if isinstance(value, str):
                return [clean_text(value)]

            if isinstance(value, list):
                return [clean_text(v) if isinstance(v, str) else str(v) for v in value]

            if isinstance(value, dict):
                cleaned_dict = {
                    k: clean_text(v) if isinstance(v, str) else v
                    for k, v in value.items()
                }
                return [json.dumps(cleaned_dict)]

            return [str(value)]
        except Exception as e:
            raise ValueError(f"Failed to normalize value: {value}") from e
