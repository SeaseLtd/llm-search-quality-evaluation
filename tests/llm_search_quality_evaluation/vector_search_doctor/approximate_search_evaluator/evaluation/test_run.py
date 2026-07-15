from pathlib import Path
from unittest.mock import MagicMock

from llm_search_quality_evaluation.shared.models import Document
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.models import (
    QuerySpec,
)
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.run import (
    build_run,
)

TEMPLATE = Path("query.json")
DOC_FIELDS = ["title"]


def _engine(*docs_per_call: list[Document]) -> MagicMock:
    """Stub engine whose fetch_for_evaluation returns docs_per_call in order."""
    engine = MagicMock()
    engine.fetch_for_evaluation.side_effect = list(docs_per_call)
    return engine


def _docs(*ids: str) -> list[Document]:
    return [Document(id=doc_id, fields={"title": doc_id}) for doc_id in ids]


class TestBuildRun:
    def test_run_keyed_by_query_text(self) -> None:
        engine = _engine(_docs("d1", "d2"))
        specs = [QuerySpec(text="my query")]
        result = build_run(engine, TEMPLATE, specs, DOC_FIELDS, top_k=10)
        assert "my query" in result

    def test_scores_are_strictly_descending(self) -> None:
        engine = _engine(_docs("d1", "d2", "d3"))
        specs = [QuerySpec(text="q")]
        result = build_run(engine, TEMPLATE, specs, DOC_FIELDS, top_k=10)
        scores = list(result["q"].values())
        assert scores == sorted(scores, reverse=True)
        assert len(set(scores)) == len(scores)  # all distinct

    def test_scores_preserve_engine_order(self) -> None:
        engine = _engine(_docs("d1", "d2", "d3"))
        specs = [QuerySpec(text="q")]
        result = build_run(engine, TEMPLATE, specs, DOC_FIELDS, top_k=10)
        assert result["q"]["d1"] > result["q"]["d2"] > result["q"]["d3"]

    def test_top_k_truncation(self) -> None:
        engine = _engine(_docs("d1", "d2", "d3", "d4", "d5"))
        specs = [QuerySpec(text="q")]
        result = build_run(engine, TEMPLATE, specs, DOC_FIELDS, top_k=3)
        assert set(result["q"].keys()) == {"d1", "d2", "d3"}

    def test_empty_result_produces_empty_dict(self) -> None:
        engine = _engine([])
        specs = [QuerySpec(text="q")]
        result = build_run(engine, TEMPLATE, specs, DOC_FIELDS, top_k=10)
        assert result["q"] == {}

    def test_fetch_called_with_correct_args(self) -> None:
        engine = _engine(_docs("d1"))
        specs = [QuerySpec(text="test query")]
        build_run(engine, TEMPLATE, specs, DOC_FIELDS, top_k=5)
        engine.fetch_for_evaluation.assert_called_once_with(
            query_template=TEMPLATE,
            doc_fields=DOC_FIELDS,
            keyword="test query",
        )

    def test_multiple_queries(self) -> None:
        engine = _engine(_docs("d1", "d2"), _docs("d3"))
        specs = [QuerySpec(text="q1"), QuerySpec(text="q2")]
        result = build_run(engine, TEMPLATE, specs, DOC_FIELDS, top_k=10)
        assert set(result.keys()) == {"q1", "q2"}
        assert result["q1"]["d1"] > result["q1"]["d2"]
        assert result["q2"]["d3"] == 10

    def test_score_formula(self) -> None:
        # top_k=5, first doc → score 5, second → 4
        engine = _engine(_docs("d1", "d2"))
        specs = [QuerySpec(text="q")]
        result = build_run(engine, TEMPLATE, specs, DOC_FIELDS, top_k=5)
        assert result["q"]["d1"] == 5
        assert result["q"]["d2"] == 4
