import requests
from typing import List, Dict, Any


class MockRequest:
    """Mock for the requests.Response.request object"""

    def __init__(self, url: str, method: str = "GET", body: str = None):
        self.url = url
        self.method = method
        self.body = body


class MockResponseDatafari:
    """
    Mock response for DatafariSearchEngine (Solr-based).
    Matches the structure expected by _search() and _get_total_hits().
    """

    def __init__(
        self,
        docs: List[Dict[str, Any]],
        total_hits: int = None,
        status_code: int = 200,
        url: str = "http://mock-datafari.com/select",
        params: Dict[str, Any] = None,
    ):
        self._docs = docs
        self.status_code = status_code
        self.total_hits = total_hits if total_hits is not None else len(docs)
        self.url = url

        # simulate request object (used in logs)
        full_url = self._build_url_with_params(url, params)
        self.request = MockRequest(full_url)

    def json(self):
        return {
            "response": {
                "docs": self._docs,
                "numFound": self.total_hits,
            }
        }

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"Status code: {self.status_code}")

    @staticmethod
    def _build_url_with_params(base_url: str, params: Dict[str, Any]):
        """Reconstruct a fake URL with query params (for logging/debug)."""
        if not params:
            return base_url

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{query_string}"
