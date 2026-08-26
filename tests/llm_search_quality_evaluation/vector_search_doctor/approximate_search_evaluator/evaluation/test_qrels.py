import logging

import pytest

from llm_search_quality_evaluation.shared.models import Document, Query, Rating
from llm_search_quality_evaluation.shared.models.evaluation_dataset_format import (
    EvaluationDataset,
)
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.qrels import (
    build_input_from_evaluation_dataset,
)


def _dataset(
    queries: list[Query],
    documents: list[Document],
    ratings: list[Rating],
    max_rating_value: int = 2,
) -> EvaluationDataset:
    return EvaluationDataset(
        queries=queries,
        documents=documents,
        ratings=ratings,
        max_rating_value=max_rating_value,
    )


@pytest.fixture
def base_dataset() -> EvaluationDataset:
    q1 = Query(id="q1", text="query one")
    q2 = Query(id="q2", text="query two")
    q3 = Query(id="q3", text="query three")  # no ratings
    docs = [
        Document(id="doc1", fields={"title": "a"}),
        Document(id="doc2", fields={"title": "b"}),
        Document(id="doc3", fields={"title": "c"}),
    ]
    ratings = [
        Rating(query_id="q1", doc_id="doc1", score=2),
        Rating(query_id="q1", doc_id="doc2", score=0),  # explicit zero
        Rating(query_id="q2", doc_id="doc3", score=1),
    ]
    return _dataset([q1, q2, q3], docs, ratings, max_rating_value=2)


class TestBuildInputFromEvaluationDataset:
    def test_qrels_keyed_by_query_text(self, base_dataset: EvaluationDataset) -> None:
        result = build_input_from_evaluation_dataset(base_dataset)
        assert "query one" in result.qrels
        assert "query two" in result.qrels

    def test_qrels_scores_are_correct(self, base_dataset: EvaluationDataset) -> None:
        result = build_input_from_evaluation_dataset(base_dataset)
        assert result.qrels["query one"]["doc1"] == 2
        assert result.qrels["query one"]["doc2"] == 0
        assert result.qrels["query two"]["doc3"] == 1

    def test_zero_score_is_present_in_qrels(
        self, base_dataset: EvaluationDataset
    ) -> None:
        result = build_input_from_evaluation_dataset(base_dataset)
        assert "doc2" in result.qrels["query one"]
        assert result.qrels["query one"]["doc2"] == 0

    def test_query_specs_one_per_rated_query(
        self, base_dataset: EvaluationDataset
    ) -> None:
        result = build_input_from_evaluation_dataset(base_dataset)
        assert len(result.query_specs) == 2
        texts = {qs.text for qs in result.query_specs}
        assert texts == {"query one", "query two"}

    def test_query_specs_extra_placeholders_empty(
        self, base_dataset: EvaluationDataset
    ) -> None:
        result = build_input_from_evaluation_dataset(base_dataset)
        for qs in result.query_specs:
            assert qs.extra_placeholders == {}

    def test_unrated_query_excluded(self, base_dataset: EvaluationDataset) -> None:
        result = build_input_from_evaluation_dataset(base_dataset)
        assert "query three" not in result.qrels
        assert all(qs.text != "query three" for qs in result.query_specs)

    def test_max_rating_value_carried_through(
        self, base_dataset: EvaluationDataset
    ) -> None:
        result = build_input_from_evaluation_dataset(base_dataset)
        assert result.max_rating_value == 2

    def test_query_specs_order_is_deterministic(
        self, base_dataset: EvaluationDataset
    ) -> None:
        r1 = build_input_from_evaluation_dataset(base_dataset)
        r2 = build_input_from_evaluation_dataset(base_dataset)
        assert [qs.text for qs in r1.query_specs] == [qs.text for qs in r2.query_specs]

    def test_unknown_query_id_in_rating_is_skipped(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        q = Query(id="q1", text="known query")
        doc = Document(id="doc1", fields={"title": "a"})
        ratings = [
            Rating(query_id="q1", doc_id="doc1", score=1),
            Rating(query_id="ghost", doc_id="doc1", score=1),  # unknown id
        ]
        dataset = _dataset([q], [doc], ratings)
        with caplog.at_level(logging.WARNING):
            result = build_input_from_evaluation_dataset(dataset)
        assert "ghost" in caplog.text
        assert len(result.qrels) == 1

    def test_duplicate_query_text_emits_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        q1 = Query(id="q1", text="same text")
        q2 = Query(id="q2", text="same text")
        doc = Document(id="doc1", fields={"title": "a"})
        ratings = [
            Rating(query_id="q1", doc_id="doc1", score=1),
            Rating(query_id="q2", doc_id="doc1", score=2),
        ]
        dataset = _dataset([q1, q2], [doc], ratings)
        with caplog.at_level(logging.WARNING):
            result = build_input_from_evaluation_dataset(dataset)
        assert "same text" in caplog.text
        # merged into one qrels entry
        assert len(result.qrels) == 1
        assert "same text" in result.qrels
