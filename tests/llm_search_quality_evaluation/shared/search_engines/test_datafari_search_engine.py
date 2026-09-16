import json
from unittest.mock import Mock

import pytest
import requests
from pydantic import HttpUrl
from requests.exceptions import HTTPError
from pydantic_core import ValidationError

from llm_search_quality_evaluation.shared.logger import configure_logging
from llm_search_quality_evaluation.dataset_generator.config import Config

from llm_search_quality_evaluation.shared.search_engines import DatafariSearchEngine
from llm_search_quality_evaluation.shared.search_engines.search_engine_base import (
    NUMBER_OF_DOCS_EACH_FETCH,
)
from llm_search_quality_evaluation.shared.models import Document

from mocks.datafari import MockResponseDatafari

import logging

configure_logging(level=logging.DEBUG)


@pytest.fixture
def datafari_config(resource_folder):
    return Config.load(resource_folder / "good_config_datafari.yaml")


@pytest.mark.parametrize("suffix", ["", "/"])
def test_fetch_all_uses_same_endpoint_for_count_and_documents(
    monkeypatch, datafari_config, mock_doc, suffix
):
    endpoint = "https://example.com/Datafari/rest/v2.0/search/vector"
    datafari_config.search_engine_url = HttpUrl(endpoint + suffix)
    get = Mock(return_value=MockResponseDatafari([mock_doc]))
    monkeypatch.setattr(requests, "get", get)
    engine = DatafariSearchEngine(
        datafari_config.search_engine_collection_endpoint,
        datafari_config.collection_name,
    )

    assert len(list(engine.fetch_all(datafari_config.doc_fields))) == 1
    assert get.call_count == 2
    for call in get.call_args_list:
        assert call.args[0] == endpoint
        assert call.kwargs["params"]["collection"] == datafari_config.collection_name


@pytest.fixture
def mock_doc():
    return {
        "id": "1",
        "exactTitle": "A first mocked title",
        "exactContent": "A first mocked description",
    }


@pytest.fixture
def expected_doc(mock_doc):
    return Document(
        id="1",
        fields={
            "exactTitle": ["A first mocked title"],
            "exactContent": ["A first mocked description"],
        },
    )


def test_datafari_fetch_for_query_generation__expects__result_returned(
    monkeypatch, datafari_config, mock_doc, expected_doc
):
    def mock_get(url, headers=None, params=None, timeout=None):
        return MockResponseDatafari([mock_doc], status_code=200, params=params)

    monkeypatch.setattr(requests, "get", mock_get)

    engine = DatafariSearchEngine("https://fakeurl", datafari_config.collection_name)

    result = engine.fetch_for_query_generation(
        documents_filter=datafari_config.documents_filter,
        number_of_docs=datafari_config.number_of_docs,
        doc_fields=datafari_config.doc_fields,
    )

    doc = result[0]

    assert doc.id == expected_doc.id
    assert doc.fields == expected_doc.fields


def test_datafari_fetch_for_evaluation__expects__result_returned(
    monkeypatch, datafari_config, mock_doc, expected_doc
):
    def mock_get(url, headers=None, params=None, timeout=None):
        return MockResponseDatafari([mock_doc], status_code=200, params=params)

    monkeypatch.setattr(requests, "get", mock_get)

    engine = DatafariSearchEngine("https://fakeurl", datafari_config.collection_name)

    result = engine.fetch_for_evaluation(
        keyword="test",
        query_template=datafari_config.query_template,
        doc_fields=datafari_config.doc_fields,
    )

    doc = result[0]

    assert doc.id == expected_doc.id
    assert doc.fields == expected_doc.fields


def test_datafari_fetch_all__expects__results_returned(
    monkeypatch, datafari_config, mock_doc, expected_doc
):
    call_counter = {"count": 0}

    def mock_get(url, headers=None, params=None, timeout=None):
        call_counter["count"] += 1

        if call_counter["count"] == 1:
            return MockResponseDatafari(
                [],
                total_hits=2 * NUMBER_OF_DOCS_EACH_FETCH,
                status_code=200,
                params=params,
            )

        elif call_counter["count"] in [2, 3]:
            return MockResponseDatafari(
                [mock_doc] * NUMBER_OF_DOCS_EACH_FETCH, status_code=200, params=params
            )

        return MockResponseDatafari([], status_code=200, params=params)

    monkeypatch.setattr(requests, "get", mock_get)

    engine = DatafariSearchEngine("https://fakeurl", datafari_config.collection_name)

    result = engine.fetch_all(
        doc_fields=datafari_config.doc_fields,
    )

    first = next(result)
    assert first.id == expected_doc.id
    assert first.fields == expected_doc.fields

    docs = [first]
    for doc in result:
        docs.append(doc)

    assert len(docs) == 2 * NUMBER_OF_DOCS_EACH_FETCH


def test_datafari_negative_fetch_for_query_generation__expects__raises_http_error(
    monkeypatch, datafari_config
):
    for status_code in [400, 401, 403, 500]:

        def mock_get(url, headers=None, params=None, timeout=None):
            return MockResponseDatafari([], status_code=status_code, params=params)

        monkeypatch.setattr(requests, "get", mock_get)

        engine = DatafariSearchEngine("https://fakeurl", datafari_config.collection_name)

        with pytest.raises(HTTPError):
            engine.fetch_for_query_generation(
                documents_filter=datafari_config.documents_filter,
                number_of_docs=datafari_config.number_of_docs,
                doc_fields=datafari_config.doc_fields,
            )


def test_datafari_negative_fetch_for_evaluation__expects__raises_http_error(
    monkeypatch, datafari_config
):
    for status_code in [400, 401, 403, 500]:

        def mock_get(url, headers=None, params=None, timeout=None):
            return MockResponseDatafari([], status_code=status_code, params=params)

        monkeypatch.setattr(requests, "get", mock_get)

        engine = DatafariSearchEngine("https://fakeurl", datafari_config.collection_name)

        with pytest.raises(HTTPError):
            engine.fetch_for_evaluation(
                keyword="test",
                query_template=datafari_config.query_template,
                doc_fields=datafari_config.doc_fields,
            )


def test_datafari_bad_url__expects__raises_validation_error():
    with pytest.raises(ValidationError):
        _ = DatafariSearchEngine("fake-NONurl", "VectorMain")


@pytest.mark.parametrize("body", [
    {"error": "Invalid query"}, [], {"response": None},
    {"response": {}}, {"response": {"docs": None}},
    {"response": {"docs": ["invalid document"]}},
])
def test_search_rejects_unexpected_response(monkeypatch, body):
    response = Mock()
    response.json.return_value = body
    monkeypatch.setattr(requests, "get", Mock(return_value=response))
    engine = DatafariSearchEngine("https://fakeurl/search", "VectorMain")

    with pytest.raises(ValueError, match="Datafari search: expected"):
        engine.fetch_for_query_generation(None, 10, [])


def test_search_accepts_empty_results(monkeypatch):
    monkeypatch.setattr(requests, "get", Mock(return_value=MockResponseDatafari([])))
    engine = DatafariSearchEngine("https://fakeurl/search", "VectorMain")
    assert engine.fetch_for_query_generation(None, 10, []) == []


@pytest.mark.parametrize("values, expected", [
    ([" comedy ", 12, "action", 4, "comedy", 2, "", 1], ["comedy", "action", "comedy"]),
    ([], []),
])
def test_fetch_field_values(monkeypatch, tmp_path, values, expected):
    template = tmp_path / "facets.json"
    template.write_text(json.dumps({"q": "*:*", "facet": True, "facet.field": "genres"}))
    response = Mock()
    response.json.return_value = {"facet_counts": {"facet_fields": {"genres": values}}}
    get = Mock(return_value=response)
    monkeypatch.setattr(requests, "get", get)
    engine = DatafariSearchEngine("https://fakeurl/search", "VectorMain")

    assert engine.fetch_field_values(template, "genres") == expected
    get.assert_called_once_with(
        "https://fakeurl/search", headers={"Accept": "application/json"},
        params={"q": "*:*", "facet": True, "facet.field": "genres",
                "wt": "json", "collection": "VectorMain"},
        timeout=30,
    )


@pytest.mark.parametrize("failure", ["http", "json", "shape"])
def test_fetch_field_values_errors(monkeypatch, tmp_path, failure):
    template = tmp_path / "facets.json"
    template.write_text('{"facet.field": "genres"}')
    response = Mock()
    if failure == "http":
        response.raise_for_status.side_effect = HTTPError("403")
        expected_error = HTTPError
    elif failure == "json":
        response.json.side_effect = requests.exceptions.JSONDecodeError("Invalid JSON", "x", 0)
        expected_error = requests.exceptions.JSONDecodeError
    else:
        response.json.return_value = {"response": {"docs": []}}
        expected_error = ValueError
    monkeypatch.setattr(requests, "get", Mock(return_value=response))
    engine = DatafariSearchEngine("https://fakeurl/search", "VectorMain")

    with pytest.raises(expected_error):
        engine.fetch_field_values(template, "genres")
