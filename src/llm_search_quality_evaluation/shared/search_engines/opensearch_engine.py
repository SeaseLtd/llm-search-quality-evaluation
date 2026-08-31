import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Union

import requests
from pydantic import HttpUrl
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException

from llm_search_quality_evaluation.shared.models.document import Document
from llm_search_quality_evaluation.shared.search_engines.search_engine_base import BaseSearchEngine
from llm_search_quality_evaluation.shared.utils import clean_text, normalize_discovered_field_values

log = logging.getLogger(__name__)


class OpenSearchEngine(BaseSearchEngine):
    """
    OpenSearch implementation to search in a given index.
    """

    def __init__(self, endpoint: HttpUrl):
        super().__init__(endpoint)
        self.HEADERS = {'Content-Type': 'application/json'}
        self.UNIQUE_KEY = "id"

    def _get_total_hits(self, payload: Dict[str, Any]) -> int:
        search_url = f"{self.endpoint}/_search"
        log.debug(f"User-specified fields: {payload.get('_source')}")
        log.debug(f"Search url: {search_url}")
        log.debug(f"OpenSearch payload (showing payload 500 first chars): {str(payload)[:500]}")
        try:
            response = requests.post(search_url, headers=self.HEADERS, json=payload)
            response.raise_for_status()
        except (ConnectionError, Timeout, RequestException, HTTPError) as e:
            log.error(f"OpenSearch query failed: {e}")
            raise

        return int(response.json().get('hits', {}).get('total', {}).get('value', 0))

    @property
    def _fetch_all_payload(self) -> Dict[str, Any]:
        return {"match_all": {}}

    def fetch_for_query_generation(self,
                                   documents_filter: Union[None, List[Dict[str, List[str]]]],
                                   number_of_docs: int,
                                   doc_fields: List[str],
                                   start: int = 0) -> List[Document]:
        """Fetches a list of documents for query generation based on optional filters."""
        log.info(f"Fetching {number_of_docs} documents (size) from the search engine for query generation")

        filters: List[Dict[str, Any]] = []
        if documents_filter:
            for field_values in documents_filter:
                for field, values in field_values.items():
                    if not values:
                        continue
                    if len(values) == 1:
                        filters.append({"term": {field: values[0]}})
                    else:
                        filters.append({"terms": {field: values}})

        fields = doc_fields if self.UNIQUE_KEY in doc_fields else doc_fields + [self.UNIQUE_KEY]

        query: Dict[str, Any] = {}
        if filters:
            query = {
                "bool": {
                    "filter": filters
                }
            }
        else:
            query = self._fetch_all_payload

        payload = {
            "query": query,
            "_source": fields,
            "from": start,
            "size": number_of_docs
        }

        return self._search(payload)

    def fetch_for_evaluation(self, query_template: Path | str, doc_fields: List[str], keyword: str = "*", extra_placeholders: Dict[str, str] | None = None) -> List[Document]:
        """Fetches documents for evaluation by executing a query built from a template."""

        log.info("Fetching documents (size) based on query template for query evaluation")

        query_template = Path(query_template)
        payload: Dict[str, Any] = self._parse_query_template(query_template, extra_placeholders)
        payload = self._replace_placeholder(payload, self.QUERY_PLACEHOLDER, keyword)

        fields = doc_fields if self.UNIQUE_KEY in doc_fields else doc_fields + [self.UNIQUE_KEY]
        payload["_source"] = fields

        return self._search(payload)

    def fetch_field_values(self, values_query_template: Path | str, field: str) -> List[str]:
        """Run an OpenSearch aggregation payload (full JSON request body) and return distinct values.

        Convention mirrors Elasticsearch: the aggregation result key under ``aggregations`` must
        equal ``field`` (the agg's internal ``terms.field`` may be a keyword subfield).

        Keyed-bucket form (``"keyed": true`` → ``buckets`` is a dict) is unsupported.
        """
        payload: Dict[str, Any] = self._parse_query_template(values_query_template)
        search_url = f"{self.endpoint}/_search"

        log.debug(f"[fetch_field_values] OpenSearch POST {search_url} payload={str(payload)[:500]}")

        try:
            response = requests.post(search_url, headers=self.HEADERS, json=payload)
            response.raise_for_status()
        except (ConnectionError, Timeout, RequestException, HTTPError) as e:
            log.error(f"OpenSearch value-discovery query failed: {e}")
            raise

        return self._list_values_from_terms_aggregations(
            response.json().get("aggregations", {}), field
        )

    @staticmethod
    def _list_values_from_terms_aggregations(aggregations: Any, field: str) -> List[str]:
        """Extract values from an OpenSearch terms aggregation response."""
        if not isinstance(aggregations, dict):
            aggregations = {}
        agg_entry = aggregations.get(field)
        if not isinstance(agg_entry, dict) or "buckets" not in agg_entry:
            raise ValueError(
                f"ES/OS value-discovery: expected aggregations.{field}.buckets in response. "
                f"Convention: the aggregation result key must equal the configured field ('{field}'); "
                f"the aggregation's internal terms.field can be a keyword subfield "
                f"(e.g. '{field}.keyword') without affecting this convention."
            )
        buckets = agg_entry["buckets"]
        if not isinstance(buckets, list):
            raise ValueError(
                f"ES/OS value-discovery: aggregations.{field}.buckets must be a list. "
                f"Keyed-bucket aggregations (`'keyed': true`) are not supported."
            )
        return normalize_discovered_field_values(bucket.get("key") for bucket in buckets)

    def _search(self, payload: Dict[str, Any]) -> List[Document]:
        """Perform a search to OpenSearch and return matching documents based on the given payload."""
        search_url = f"{self.endpoint}/_search"
        log.debug(f"User-specified fields: {payload.get('_source')}")
        log.debug(f"Search url: {search_url}")
        log.debug(f"OpenSearch payload (showing payload 500 first chars): {str(payload)[:500]}")
        try:
            response = requests.post(search_url, headers=self.HEADERS, json=payload)
            response.raise_for_status()
        except (ConnectionError, Timeout, RequestException, HTTPError) as e:
            log.error(f"OpenSearch query failed: {e}")
            raise

        hits = response.json().get("hits", {}).get("hits", [])
        result = []

        for hit in hits:
            source = hit.get("_source", {})
            log.debug(f"Opensearch returns fields based on payload: {list(source.items())}")
            doc_id = source.get("id", hit.get("_id"))

            fields = {
                key: self._normalize(value)
                for key, value in source.items()
                if key != "id"
            }

            result.append(Document(id=doc_id, fields=fields))
        log.info(f"Fetched {len(result)} documents from the engine")
        return result

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
