import pytest
from pydantic import HttpUrl

from llm_search_quality_evaluation.shared.search_engines import SearchEngineFactory, VespaSearchEngine, DatafariSearchEngine


def test_build_datafari():
    engine = SearchEngineFactory.build(
        "datafari", HttpUrl("https://example.com/search"), collection_name="VectorMain"
    )
    assert isinstance(engine, DatafariSearchEngine)
    assert engine.collection_name == "VectorMain"


def test_build_datafari_requires_collection():
    with pytest.raises(ValueError, match="collection_name is required"):
        SearchEngineFactory.build("datafari", HttpUrl("https://example.com/search"))


def test_build_vespa__expects__vespa_search_engine():
    search_engine = SearchEngineFactory.build(
        search_engine_type="vespa",
        endpoint=HttpUrl("http://localhost:8080/doc/"),
    )

    assert isinstance(search_engine, VespaSearchEngine)


def test_build_unsupported_search_engine__expects__value_error():
    with pytest.raises(ValueError, match="Unsupported search engine: unsupported"):
        SearchEngineFactory.build(
            search_engine_type="unsupported",
            endpoint=HttpUrl("http://localhost:8080/doc/"),
        )
