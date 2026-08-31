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
        """Yield all documents in fixed-size batches without loading the full result
        into memory."""
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
        """Run an engine-native facet, aggregation, or grouping template.

        Return distinct ``field`` values as non-empty, stripped strings. An empty
        result returns ``[]`` silently; the caller warns. Malformed response paths
        raise ``ValueError``; HTTP and JSON errors propagate with engine context.
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
