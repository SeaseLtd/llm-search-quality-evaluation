import gzip
import json
import types
from pathlib import Path
from unittest.mock import MagicMock

import jsonlines
import pytest

from llm_search_quality_evaluation.shared.models import Document
from llm_search_quality_evaluation.shared.models.evaluation_dataset_format import EvaluationDataset
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator import main as main_mod
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.results import (
    RESULTS_FILENAME,
)


def _write_dataset(path: Path, dataset: EvaluationDataset) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(dataset.model_dump(), f)


def _make_dataset(
    num_queries: int = 2,
    max_rating_value: int = 4,
) -> EvaluationDataset:
    queries = [{"id": f"q{i}", "text": f"query {i}"} for i in range(num_queries)]
    documents = [{"id": f"d{i}", "fields": {"title": [f"doc {i}"]}} for i in range(num_queries)]
    ratings = [
        {"query_id": f"q{i}", "doc_id": f"d{i}", "score": max_rating_value}
        for i in range(num_queries)
    ]
    return EvaluationDataset(
        queries=queries,
        documents=documents,
        ratings=ratings,
        max_rating_value=max_rating_value,
    )


def _stub_engine(num_queries: int) -> MagicMock:
    engine = MagicMock()
    engine.fetch_for_evaluation.return_value = [
        Document(id=f"d{i}", fields={"title": [f"doc {i}"]}) for i in range(num_queries)
    ]
    return engine


def _write_embeddings(path: Path, entries: list[dict]) -> None:
    with jsonlines.open(path, mode="w") as writer:
        for entry in entries:
            writer.write(entry)


def _make_config(
    tmp_path: Path,
    dataset_path: Path,
    output_path: Path,
    *,
    template_text: str = '{"query": "$query"}',
    embeddings_file: Path | None = None,
) -> object:
    """Build a minimal Config-like namespace for monkeypatching."""
    query_template = tmp_path / "template.json"
    query_template.write_text(template_text)

    return types.SimpleNamespace(
        search_engine_type="solr",
        search_engine_collection_endpoint="http://localhost:8983/solr/testcore/",
        evaluation_dataset_path=dataset_path,
        embeddings_file=embeddings_file,
        query_template=query_template,
        doc_fields=[],
        top_k=10,
        metrics=["ndcg@10", "map@10"],
        output_destination=output_path,
    )


class TestMainOrchestration:
    def test_main_writes_results_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        dataset = _make_dataset(num_queries=2)
        dataset_path = tmp_path / "evaluation_dataset.json.gz"
        _write_dataset(dataset_path, dataset)
        output_path = tmp_path / "output"
        config = _make_config(tmp_path, dataset_path, output_path)

        monkeypatch.setattr(main_mod, "Config", types.SimpleNamespace(load=lambda _: config))
        monkeypatch.setattr(main_mod, "_parse_args", lambda: types.SimpleNamespace(config="ignored.yaml", verbose=False))
        monkeypatch.setattr(main_mod, "SearchEngineFactory", types.SimpleNamespace(
            build=lambda **_: _stub_engine(2)
        ))

        main_mod.main()

        assert (output_path / RESULTS_FILENAME).exists()

    def test_main_results_have_expected_keys(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        dataset = _make_dataset(num_queries=2, max_rating_value=4)
        dataset_path = tmp_path / "evaluation_dataset.json.gz"
        _write_dataset(dataset_path, dataset)
        output_path = tmp_path / "output"
        config = _make_config(tmp_path, dataset_path, output_path)

        monkeypatch.setattr(main_mod, "Config", types.SimpleNamespace(load=lambda _: config))
        monkeypatch.setattr(main_mod, "_parse_args", lambda: types.SimpleNamespace(config="ignored.yaml", verbose=False))
        monkeypatch.setattr(main_mod, "SearchEngineFactory", types.SimpleNamespace(
            build=lambda **_: _stub_engine(2)
        ))

        main_mod.main()

        data = json.loads((output_path / RESULTS_FILENAME).read_text())
        for key in ("search_engine", "query_template", "top_k", "max_rating_value",
                    "relevance_threshold", "num_queries", "metrics", "aggregate", "per_query"):
            assert key in data, f"missing key: {key}"

    def test_main_derived_relevance_threshold(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # max_rating_value=4 → threshold = (4+1)//2 = 2
        dataset = _make_dataset(num_queries=2, max_rating_value=4)
        dataset_path = tmp_path / "evaluation_dataset.json.gz"
        _write_dataset(dataset_path, dataset)
        output_path = tmp_path / "output"
        config = _make_config(tmp_path, dataset_path, output_path)

        monkeypatch.setattr(main_mod, "Config", types.SimpleNamespace(load=lambda _: config))
        monkeypatch.setattr(main_mod, "_parse_args", lambda: types.SimpleNamespace(config="ignored.yaml", verbose=False))
        monkeypatch.setattr(main_mod, "SearchEngineFactory", types.SimpleNamespace(
            build=lambda **_: _stub_engine(2)
        ))

        main_mod.main()

        data = json.loads((output_path / RESULTS_FILENAME).read_text())
        assert data["max_rating_value"] == 4
        assert data["relevance_threshold"] == 2

    def test_main_empty_dataset_exits_nonzero(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # Dataset with no queries, no ratings
        empty_dataset = EvaluationDataset(queries=[], documents=[], ratings=[], max_rating_value=4)
        dataset_path = tmp_path / "evaluation_dataset.json.gz"
        _write_dataset(dataset_path, empty_dataset)
        output_path = tmp_path / "output"
        config = _make_config(tmp_path, dataset_path, output_path)

        monkeypatch.setattr(main_mod, "Config", types.SimpleNamespace(load=lambda _: config))
        monkeypatch.setattr(main_mod, "_parse_args", lambda: types.SimpleNamespace(config="ignored.yaml", verbose=False))
        monkeypatch.setattr(main_mod, "SearchEngineFactory", types.SimpleNamespace(
            build=lambda **_: _stub_engine(0)
        ))

        with pytest.raises(SystemExit) as exc_info:
            main_mod.main()
        assert exc_info.value.code != 0

    def test_main_vector_template_without_embeddings_file_raises(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        dataset = _make_dataset(num_queries=2)
        dataset_path = tmp_path / "evaluation_dataset.json.gz"
        _write_dataset(dataset_path, dataset)
        output_path = tmp_path / "output"
        config = _make_config(
            tmp_path,
            dataset_path,
            output_path,
            template_text='{"q": "{!knn f=vector topK=10}$vector"}',
        )

        monkeypatch.setattr(main_mod, "Config", types.SimpleNamespace(load=lambda _: config))
        monkeypatch.setattr(main_mod, "_parse_args", lambda: types.SimpleNamespace(config="ignored.yaml", verbose=False))
        monkeypatch.setattr(main_mod, "SearchEngineFactory", types.SimpleNamespace(
            build=lambda **_: _stub_engine(2)
        ))

        with pytest.raises(ValueError, match=r"requires \$vector, but embeddings_file is not set"):
            main_mod.main()

    def test_main_vector_template_with_missing_embeddings_raises(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        dataset = _make_dataset(num_queries=2)
        dataset_path = tmp_path / "evaluation_dataset.json.gz"
        _write_dataset(dataset_path, dataset)
        output_path = tmp_path / "output"
        embeddings_file = tmp_path / "queries_embeddings.jsonl"
        _write_embeddings(
            embeddings_file,
            [{"id": "q0", "vector": [0.1, 0.2]}],
        )
        config = _make_config(
            tmp_path,
            dataset_path,
            output_path,
            template_text='{"q": "{!knn f=vector topK=10}$vector"}',
            embeddings_file=embeddings_file,
        )

        monkeypatch.setattr(main_mod, "Config", types.SimpleNamespace(load=lambda _: config))
        monkeypatch.setattr(main_mod, "_parse_args", lambda: types.SimpleNamespace(config="ignored.yaml", verbose=False))
        monkeypatch.setattr(main_mod, "SearchEngineFactory", types.SimpleNamespace(
            build=lambda **_: _stub_engine(2)
        ))

        with pytest.raises(ValueError, match=r"Missing \$vector values for 1 query\(s\): 'query 1'"):
            main_mod.main()
