import pytest
import requests
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
    def mock_get(url, headers=None, params=None):
        return MockResponseDatafari([mock_doc], status_code=200, params=params)

    monkeypatch.setattr(requests, "get", mock_get)

    engine = DatafariSearchEngine("https://fakeurl")

    result = engine.fetch_for_query_generation(
        documents_filter=datafari_config.documents_filter,
        number_of_docs=datafari_config.number_of_docs,
        doc_fields=datafari_config.doc_fields,
        collection=datafari_config.collection_name,
    )

    doc = result[0]

    assert doc.id == expected_doc.id
    assert doc.fields == expected_doc.fields


def test_datafari_fetch_for_evaluation__expects__result_returned(
    monkeypatch, datafari_config, mock_doc, expected_doc
):
    def mock_get(url, headers=None, params=None):
        return MockResponseDatafari([mock_doc], status_code=200, params=params)

    monkeypatch.setattr(requests, "get", mock_get)

    engine = DatafariSearchEngine("https://fakeurl")

    result = engine.fetch_for_evaluation(
        keyword="test",
        query_template=datafari_config.query_template,
        doc_fields=datafari_config.doc_fields,
        collection=datafari_config.collection_name,
    )

    doc = result[0]

    assert doc.id == expected_doc.id
    assert doc.fields == expected_doc.fields


def test_datafari_fetch_all__expects__results_returned(
    monkeypatch, datafari_config, mock_doc, expected_doc
):
    call_counter = {"count": 0}

    def mock_get(url, headers=None, params=None):
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

    engine = DatafariSearchEngine("https://fakeurl")

    result = engine.fetch_all(
        doc_fields=datafari_config.doc_fields,
        collection=datafari_config.collection_name,
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

        def mock_get(url, headers=None, params=None):
            return MockResponseDatafari([], status_code=status_code, params=params)

        monkeypatch.setattr(requests, "get", mock_get)

        engine = DatafariSearchEngine("https://fakeurl")

        with pytest.raises(HTTPError):
            engine.fetch_for_query_generation(
                documents_filter=datafari_config.documents_filter,
                number_of_docs=datafari_config.number_of_docs,
                doc_fields=datafari_config.doc_fields,
                collection=datafari_config.collection_name,
            )


def test_datafari_negative_fetch_for_evaluation__expects__raises_http_error(
    monkeypatch, datafari_config
):
    for status_code in [400, 401, 403, 500]:

        def mock_get(url, headers=None, params=None):
            return MockResponseDatafari([], status_code=status_code, params=params)

        monkeypatch.setattr(requests, "get", mock_get)

        engine = DatafariSearchEngine("https://fakeurl")

        with pytest.raises(HTTPError):
            engine.fetch_for_evaluation(
                keyword="test",
                query_template=datafari_config.query_template,
                doc_fields=datafari_config.doc_fields,
                collection=datafari_config.collection_name,
            )


def test_datafari_bad_url__expects__raises_validation_error():
    with pytest.raises(ValidationError):
        _ = DatafariSearchEngine("fake-NONurl")
