import json
from pathlib import Path

import jsonlines
import pytest

from llm_search_quality_evaluation.shared.models import Query
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.embeddings import (
    attach_vectors,
    load_query_vectors,
)
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.models import (
    QuerySpec,
)


def _write_embeddings(path: Path, entries: list[dict]) -> None:
    with jsonlines.open(path, mode="w") as writer:
        for entry in entries:
            writer.write(entry)


@pytest.fixture
def queries() -> list[Query]:
    return [
        Query(id="q1", text="find cats"),
        Query(id="q2", text="find dogs"),
    ]


class TestLoadQueryVectors:
    def test_returns_text_to_vector_string(self, tmp_path: Path, queries: list[Query]) -> None:
        emb_file = tmp_path / "queries_embeddings.jsonl"
        _write_embeddings(emb_file, [
            {"id": "q1", "vector": [0.1, 0.2, 0.3]},
            {"id": "q2", "vector": [0.4, 0.5, 0.6]},
        ])
        result = load_query_vectors(emb_file, queries)
        assert result["find cats"] == json.dumps([0.1, 0.2, 0.3])
        assert result["find dogs"] == json.dumps([0.4, 0.5, 0.6])

    def test_vector_string_is_valid_json(self, tmp_path: Path, queries: list[Query]) -> None:
        emb_file = tmp_path / "queries_embeddings.jsonl"
        _write_embeddings(emb_file, [{"id": "q1", "vector": [0.1, 0.2]}])
        result = load_query_vectors(emb_file, queries)
        parsed = json.loads(result["find cats"])
        assert parsed == [0.1, 0.2]

    def test_unknown_query_id_skipped(self, tmp_path: Path, queries: list[Query], caplog: pytest.LogCaptureFixture) -> None:
        emb_file = tmp_path / "queries_embeddings.jsonl"
        _write_embeddings(emb_file, [
            {"id": "q1", "vector": [0.1]},
            {"id": "ghost", "vector": [0.9]},
        ])
        import logging
        with caplog.at_level(logging.WARNING):
            result = load_query_vectors(emb_file, queries)
        assert "ghost" in caplog.text
        assert "find cats" in result
        assert len(result) == 1


class TestAttachVectors:
    def test_sets_vector_placeholder(self) -> None:
        specs = [QuerySpec(text="find cats"), QuerySpec(text="find dogs")]
        text_to_vector = {"find cats": "[0.1, 0.2]"}
        result = attach_vectors(specs, text_to_vector)
        assert result[0].extra_placeholders["$vector"] == "[0.1, 0.2]"

    def test_spec_without_vector_unchanged(self) -> None:
        specs = [QuerySpec(text="find cats"), QuerySpec(text="find dogs")]
        text_to_vector = {"find cats": "[0.1, 0.2]"}
        result = attach_vectors(specs, text_to_vector)
        assert result[1].extra_placeholders == {}

    def test_custom_placeholder(self) -> None:
        specs = [QuerySpec(text="q")]
        result = attach_vectors(specs, {"q": "[1.0]"}, placeholder="$emb")
        assert "$emb" in result[0].extra_placeholders
        assert "$vector" not in result[0].extra_placeholders

    def test_original_specs_not_mutated(self) -> None:
        spec = QuerySpec(text="find cats")
        attach_vectors([spec], {"find cats": "[0.1]"})
        assert spec.extra_placeholders == {}

    def test_empty_text_to_vector_returns_unchanged(self) -> None:
        specs = [QuerySpec(text="q")]
        result = attach_vectors(specs, {})
        assert result[0].extra_placeholders == {}
