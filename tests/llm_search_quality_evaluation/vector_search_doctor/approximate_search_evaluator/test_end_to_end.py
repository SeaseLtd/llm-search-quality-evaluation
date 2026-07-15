"""
End-to-end test: metric correctness with a mocked engine.

Covers exact pre-computed metric values for a perfect and an imperfect ranking.
Wiring assertions (keys present, empty-input error) are in test_main.py.
"""
import gzip
import json
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from llm_search_quality_evaluation.shared.models import Document
from llm_search_quality_evaluation.shared.models.evaluation_dataset_format import EvaluationDataset
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator import main as main_mod
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.results import (
    RESULTS_FILENAME,
)

# ---------------------------------------------------------------------------
# Pre-computed expected values (computed via ranx directly, see docs/05-plan)
#
# Dataset: max_rating_value=4  →  relevance_threshold = (4+1)//2 = 2
#
# "imperfect" query: d3 rated 4, d4 rated 3 (both ≥ threshold).
#   Engine returns [d4, d3]  →  wrong order.
#   ndcg@2 ≈ 0.9134015909...   precision@2 = 1.0   recall@2 = 1.0
#
# "perfect" query: d1 rated 4, d2 rated 3 (both ≥ threshold).
#   Engine returns [d1, d2]  →  correct order.
#   ndcg@2 = 1.0              precision@2 = 1.0   recall@2 = 1.0
#
# Query names are kept in alphabetical order so that ranx's internal sort
# and the qrels insertion order agree, making the per-query mapping stable.
# ---------------------------------------------------------------------------

_MAX_RATING = 4
_METRICS = ["ndcg@2", "precision@2", "recall@2"]

_EXPECTED_IMPERFECT_NDCG = pytest.approx(0.9134015909, abs=1e-6)
_EXPECTED_PERFECT_NDCG = pytest.approx(1.0, abs=1e-6)


def _build_dataset() -> EvaluationDataset:
    # "imperfect" inserted before "perfect" (alphabetical = ranx sort order)
    return EvaluationDataset(
        queries=[
            {"id": "qi", "text": "imperfect"},
            {"id": "qp", "text": "perfect"},
        ],
        documents=[
            {"id": "d1", "fields": {"title": ["doc 1"]}},
            {"id": "d2", "fields": {"title": ["doc 2"]}},
            {"id": "d3", "fields": {"title": ["doc 3"]}},
            {"id": "d4", "fields": {"title": ["doc 4"]}},
        ],
        ratings=[
            {"query_id": "qi", "doc_id": "d3", "score": 4},
            {"query_id": "qi", "doc_id": "d4", "score": 3},
            {"query_id": "qp", "doc_id": "d1", "score": 4},
            {"query_id": "qp", "doc_id": "d2", "score": 3},
        ],
        max_rating_value=_MAX_RATING,
    )


def _write_dataset(path: Path, dataset: EvaluationDataset) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(dataset.model_dump(mode="json"), f)


def _stub_engine() -> MagicMock:
    """Return docs per keyword: imperfect query → wrong order; perfect → right order."""
    engine = MagicMock()

    def _fetch(**kwargs: object) -> list[Document]:
        keyword = kwargs.get("keyword", "")
        if keyword == "imperfect":
            return [
                Document(id="d4", fields={"title": ["doc 4"]}),
                Document(id="d3", fields={"title": ["doc 3"]}),
            ]
        return [
            Document(id="d1", fields={"title": ["doc 1"]}),
            Document(id="d2", fields={"title": ["doc 2"]}),
        ]

    engine.fetch_for_evaluation.side_effect = _fetch
    return engine


def _make_config(tmp_path: Path, dataset_path: Path, output_path: Path, engine_type: str) -> object:
    query_template = tmp_path / "template.json"
    query_template.write_text('{"query": "$query"}')
    return types.SimpleNamespace(
        search_engine_type=engine_type,
        search_engine_collection_endpoint=f"http://localhost:8983/{engine_type}/testcore/",
        evaluation_dataset_path=dataset_path,
        embeddings_folder=None,
        query_template=query_template,
        doc_fields=[],
        top_k=2,
        metrics=_METRICS,
        output_destination=output_path,
    )


@pytest.fixture
def e2e_setup(tmp_path: Path):
    dataset = _build_dataset()
    dataset_path = tmp_path / "evaluation_dataset.json.gz"
    _write_dataset(dataset_path, dataset)
    output_path = tmp_path / "output"
    return dataset_path, output_path


@pytest.mark.parametrize("engine_type", ["solr", "opensearch"])
class TestEndToEnd:
    def _run_main(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        dataset_path: Path,
        output_path: Path,
        engine_type: str,
    ) -> dict:
        config = _make_config(tmp_path, dataset_path, output_path, engine_type)
        monkeypatch.setattr(main_mod, "Config", types.SimpleNamespace(load=lambda _: config))
        monkeypatch.setattr(main_mod, "_parse_args", lambda: types.SimpleNamespace(config="ignored.yaml", verbose=False))
        monkeypatch.setattr(main_mod, "SearchEngineFactory", types.SimpleNamespace(
            build=lambda **_: _stub_engine()
        ))
        main_mod.main()
        return json.loads((output_path / RESULTS_FILENAME).read_text())

    def test_perfect_query_ndcg_is_one(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, e2e_setup: tuple, engine_type: str
    ) -> None:
        dataset_path, output_path = e2e_setup
        data = self._run_main(monkeypatch, tmp_path, dataset_path, output_path, engine_type)
        assert data["per_query"]["perfect"]["ndcg@2"] == _EXPECTED_PERFECT_NDCG

    def test_imperfect_query_ndcg_precomputed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, e2e_setup: tuple, engine_type: str
    ) -> None:
        dataset_path, output_path = e2e_setup
        data = self._run_main(monkeypatch, tmp_path, dataset_path, output_path, engine_type)
        assert data["per_query"]["imperfect"]["ndcg@2"] == _EXPECTED_IMPERFECT_NDCG

    def test_aggregate_in_unit_interval(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, e2e_setup: tuple, engine_type: str
    ) -> None:
        dataset_path, output_path = e2e_setup
        data = self._run_main(monkeypatch, tmp_path, dataset_path, output_path, engine_type)
        for metric, value in data["aggregate"].items():
            assert 0.0 <= value <= 1.0, f"{metric}={value} out of [0,1]"

    def test_per_query_counts(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, e2e_setup: tuple, engine_type: str
    ) -> None:
        dataset_path, output_path = e2e_setup
        data = self._run_main(monkeypatch, tmp_path, dataset_path, output_path, engine_type)
        # Both queries: engine returns 2 docs, 2 relevant in ground truth
        for query in ("perfect", "imperfect"):
            assert data["per_query"][query]["num_retrieved"] == 2.0
            assert data["per_query"][query]["num_relevant_total"] == 2.0

    def test_relevance_threshold_derived(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, e2e_setup: tuple, engine_type: str
    ) -> None:
        dataset_path, output_path = e2e_setup
        data = self._run_main(monkeypatch, tmp_path, dataset_path, output_path, engine_type)
        # (4+1)//2 = 2
        assert data["relevance_threshold"] == 2
        assert data["max_rating_value"] == _MAX_RATING
