import json
from abc import ABC, abstractmethod
from json import JSONDecodeError
from pathlib import Path
from typing import List, Dict, Any, Union, Iterator, Optional
from pydantic import HttpUrl
from llm_search_quality_evaluation.shared.models.document import Document

NUMBER_OF_DOCS_EACH_FETCH = 100


class BaseSearchEngine(ABC):
    s = {
        "\\",
        "+",
        "-",
        "!",
        "(",
        ")",
        ":",
        "^",
        "[",
        "]",
        '"',
        "{",
        "}",
        "~",
        "*",
        "?",
        "|",
        "&",
        "/",
    }
    SPECIAL_CHARS: set[str] = s

    def __init__(self, endpoint: HttpUrl):
        self.endpoint = HttpUrl(endpoint)
        self.QUERY_PLACEHOLDER = "$query"
        self.UNIQUE_KEY = "id"

    @staticmethod
    def escape(string: str) -> str:
        """Escape special characters used in query syntax."""
        sb = []
        for c in string:
            if c in BaseSearchEngine.SPECIAL_CHARS:
                sb.append("\\")
            sb.append(c)
        return "".join(sb)

    def fetch_all(
        self, doc_fields: List[str], collection: Optional[str] = None
    ) -> Iterator[Document]:
        """Extract all documents from search engine in batches.

        Yields batches of documents instead of loading everything in memory.

        Args:
            doc_fields: Fields to extract from documents

        Yields:
            List[Document]: Batch of documents
        """
        # Now this is relying on fetch_for_query_generation to avoid duplicate code. Might be changed in the future
        start: int = 0
        if collection is not None:
            total_hits: int = self._get_total_hits(self._fetch_all_payload, collection)
        else:
            total_hits = self._get_total_hits(self._fetch_all_payload, collection)

        while start < total_hits:
            batch = self.fetch_for_query_generation(
                documents_filter=None,
                number_of_docs=NUMBER_OF_DOCS_EACH_FETCH,
                doc_fields=doc_fields,
                start=start,
                collection=collection,
            )
            if not batch:
                break
            for doc in batch:
                yield doc
            # if we didn't reach the end of the docs, then len(batch) == NUMBER_OF_DOCS_EACH_FETCH if we reached the
            # end of the docs. then len(batch) <= NUMBER_OF_DOCS_EACH_FETCH -> next iteration we exit the loop since
            # we are adding NUMBER_OF_DOCS_EACH_FETCH (not len(batch)) and start becomes greater than total_hits
            start += NUMBER_OF_DOCS_EACH_FETCH

    def _parse_query_template(
        self, path: Path | str, extra_placeholders: Dict[str, str] | None = None
    ) -> Dict[str, Any]:
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

    def _replace_placeholder(
        self, obj: Any, placeholder: str, keyword: str | None
    ) -> Any:
        if keyword is None:
            return obj

        if isinstance(obj, str):
            return obj.replace(placeholder, keyword)
        elif isinstance(obj, dict):
            return {
                k: self._replace_placeholder(v, placeholder, keyword)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [self._replace_placeholder(x, placeholder, keyword) for x in obj]
        else:
            return obj

    @abstractmethod
    def fetch_for_query_generation(
        self,
        documents_filter: Union[None, List[Dict[str, List[str]]]],
        number_of_docs: int,
        doc_fields: List[str],
        start: int = 0,
        collection: Optional[str] = None,
    ) -> List[Document]:
        """Extract documents for generating queries."""
        pass

    @abstractmethod
    def fetch_for_evaluation(
        self,
        query_template: Path | str,
        doc_fields: List[str],
        keyword: str = "*:*",
        collection: Optional[str] = None,
    ) -> List[Document]:
        """Search for documents based on a keyword and a query template to evaluate the system."""
        pass

    @abstractmethod
    def _search(self, payload: Dict[str, Any]) -> List[Document]:
        """Search for documents using a query."""
        pass

    @abstractmethod
    def _get_total_hits(
        self, payload: Dict[str, Any], collection: Optional[str]
    ) -> int:
        """Get the total number of documents returned by a query."""
        pass

    @property
    @abstractmethod
    def _fetch_all_payload(self) -> Dict[str, Any]:
        """Payload to fetch all documents from the search engine."""
        pass

    def _apply_extra_placeholders(
        self, text: str, extra_placeholders: Dict[str, str] | None
    ) -> str:
        """Substitute extra_placeholders verbatim in raw template text before JSON parsing."""
        if not extra_placeholders:
            return text
        for placeholder, value in extra_placeholders.items():
            text = text.replace(placeholder, value)
        return text
