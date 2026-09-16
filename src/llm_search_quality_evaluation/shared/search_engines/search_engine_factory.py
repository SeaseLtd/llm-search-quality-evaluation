from typing import Dict, Optional, Type
from pydantic import HttpUrl

from llm_search_quality_evaluation.shared.search_engines.opensearch_engine import OpenSearchEngine
from llm_search_quality_evaluation.shared.search_engines.search_engine_base import BaseSearchEngine
from llm_search_quality_evaluation.shared.search_engines.solr_search_engine import SolrSearchEngine
from llm_search_quality_evaluation.shared.search_engines.elasticsearch_search_engine import ElasticsearchSearchEngine
from llm_search_quality_evaluation.shared.search_engines.vespa_search_engine import VespaSearchEngine
from llm_search_quality_evaluation.shared.search_engines.datafari_search_engine import DatafariSearchEngine

import logging

log = logging.getLogger(__name__)


class SearchEngineFactory:
    SEARCH_ENGINE_REGISTRY: Dict[str, Type[BaseSearchEngine]] = {
        "solr": SolrSearchEngine,
        "opensearch": OpenSearchEngine,
        "elasticsearch": ElasticsearchSearchEngine,
        "vespa": VespaSearchEngine,
        "datafari": DatafariSearchEngine,        
    }

    @classmethod
    def build(cls, search_engine_type: str, endpoint: HttpUrl, collection_name: Optional[str] = None) -> BaseSearchEngine:

        if search_engine_type == "datafari":
            if not collection_name:
                raise ValueError("collection_name is required for the Datafari search engine")
            return DatafariSearchEngine(endpoint, collection_name)
        if search_engine_type not in cls.SEARCH_ENGINE_REGISTRY:
            log.error("Unsupported search engine requested: %s", search_engine_type)
            raise ValueError(f"Unsupported search engine: {search_engine_type}")
        log.info("Searching in %s at endpoint : %s", search_engine_type.upper(), endpoint)
        return cls.SEARCH_ENGINE_REGISTRY[search_engine_type](endpoint)
