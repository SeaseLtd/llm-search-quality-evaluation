import json
from abc import ABC, abstractmethod
from json import JSONDecodeError
from pathlib import Path
from typing import List, Dict, Any, Union, Iterator
from pydantic import HttpUrl
from llm_search_quality_evaluation.shared.models.document import Document

NUMBER_OF_DOCS_EACH_FETCH = 100

class BaseSearchEngine(ABC):

    s = {'\\', '+', '-', '!', '(', ')', ':', '^', '[', ']', '"',
         '{', '}', '~', '*', '?', '|', '&', '/'}
    SPECIAL_CHARS: set[str] = s

    # Engine-specific placeholder convention used in query templates. Subclasses override
    # when their engine uses a different convention (e.g. Vespa uses YQL '@kw').
    QUERY_PLACEHOLDER: str = "$query"

    def __init__(self, endpoint: HttpUrl):
        self.endpoint = HttpUrl(endpoint)
        self.UNIQUE_KEY = 'id'

    @staticmethod
    def escape(string: str) -> str:
        """Escape special characters used in query syntax."""
        sb = []
        for c in string:
            if c in BaseSearchEngine.SPECIAL_CHARS:
                sb.append('\\')
            sb.append(c)
        return ''.join(sb)

    def fetch_all(self, doc_fields: List[str]) -> Iterator[Document]:
        """Extract all documents from search engine in batches.

        Yields batches of documents instead of loading everything in memory.

        Args:
            doc_fields: Fields to extract from documents

        Yields:
            List[Document]: Batch of documents
        """
        # Now this is relying on fetch_for_query_generation to avoid duplicate code. Might be changed in the future
        start: int = 0
        total_hits: int = self._get_total_hits(self._fetch_all_payload)
        while start < total_hits:
            batch = self.fetch_for_query_generation(
                documents_filter=None,
                number_of_docs=NUMBER_OF_DOCS_EACH_FETCH,
                doc_fields=doc_fields,
                start=start
                )
            if not batch:
                break
            for doc in batch:
                yield doc
            # if we didn't reach the end of the docs, then len(batch) == NUMBER_OF_DOCS_EACH_FETCH if we reached the
            # end of the docs. then len(batch) <= NUMBER_OF_DOCS_EACH_FETCH -> next iteration we exit the loop since
            # we are adding NUMBER_OF_DOCS_EACH_FETCH (not len(batch)) and start becomes greater than total_hits
            start += NUMBER_OF_DOCS_EACH_FETCH


    def _parse_query_template(self, path: Path | str, extra_placeholders: Dict[str, str] | None = None) -> Dict[str, Any]:
        """Return the payload, applying extra_placeholders verbatim before JSON parsing."""
        path = Path(path)
        try:
            with path.open() as f:
                text = f.read()
            text = self._apply_extra_placeholders(text, extra_placeholders)
            data: Dict[str, Any] = json.loads(text)
            return data
        except JSONDecodeError as e:
            raise ValueError(f"Invalid JSON query_template: {e}")

    def _replace_placeholder(self, obj: Any, placeholder: str, keyword: str | None) -> Any:
        if keyword is None:
            return obj

        if isinstance(obj, str):
            return obj.replace(placeholder, keyword)
        elif isinstance(obj, dict):
            return {k: self._replace_placeholder(v, placeholder, keyword) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_placeholder(x, placeholder, keyword) for x in obj]
        else:
            return obj


    @abstractmethod
    def fetch_for_query_generation(self,
                                   documents_filter: Union[None, List[Dict[str, List[str]]]],
                                   number_of_docs: int,
                                   doc_fields: List[str],
                                   start: int = 0) \
            -> List[Document]:
        """Extract documents for generating queries."""
        pass

    @abstractmethod
    def fetch_for_evaluation(self,
                             query_template: Path | str,
                             doc_fields: List[str],
                             keyword: str="*:*",
                             extra_placeholders: Dict[str, str] | None = None) \
            -> List[Document]:
        """Search for documents based on a keyword and a query template to evaluate the system."""
        pass

    def _apply_extra_placeholders(self, text: str, extra_placeholders: Dict[str, str] | None) -> str:
        """Substitute extra_placeholders verbatim in raw template text before JSON parsing."""
        if not extra_placeholders:
            return text
        for placeholder, value in extra_placeholders.items():
            text = text.replace(placeholder, value)
        return text

    @abstractmethod
    def fetch_field_values(self, values_query_template: Path | str, field: str) -> List[str]:
        """Run an engine-native facet/aggregation/grouping payload and return the distinct values
        produced for ``field``.

        Per-engine transport (deliberately different so each engine matches its existing
        retrieval convention):

        - **Solr** — the template is a JSON dict of Solr request *parameters* (``q``, ``facet``,
          ``facet.field``, ``facet.limit``, ``rows``, ...). Parsed with ``_parse_query_template``,
          ``wt=json`` is injected, and the call is ``GET /select?<params>`` (NOT a Solr JSON
          Request API body).
        - **Elasticsearch / OpenSearch** — the template is the full JSON request body, POSTed
          to ``_search`` unchanged.
        - **Vespa** — the template is YQL only; the implementation wraps it with
          ``{"yql": <file>, "hits": 0, "presentation.format": "json"}`` and POSTs.

        The template's limit (Solr ``facet.limit``, ES/OS terms ``size``, Vespa grouping
        ``max(N)``) is the only knob — there is no separate config option.

        Return values are normalized to non-empty stripped strings via
        ``shared.utils.normalize_discovered_field_values`` (containers raise).

        Empty result (response path exists but contains zero buckets/values) → return ``[]``
        *silently*. The single warning lives in ``add_category_queries`` so it carries full
        source context (``field``, ``values_query_template_file``).

        Missing/wrong-typed/wrong-key response path → raise ``ValueError`` with engine context.
        HTTP/JSON parse errors propagate or are wrapped with engine context.
        """
        pass

    @abstractmethod
    def _search(self, payload: Dict[str, Any]) -> List[Document]:
        """Search for documents using a query."""
        pass

    @abstractmethod
    def _get_total_hits(self, payload: Dict[str, Any]) -> int:
        """Get the total number of documents returned by a query."""
        pass

    @property
    @abstractmethod
    def _fetch_all_payload(self) -> Dict[str, Any]:
        """Payload to fetch all documents from the search engine."""
        pass

