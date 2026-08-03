import json
from pathlib import Path

from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.models import (
    EvaluationMeta,
    EvaluationResult,
    SearchEngineMeta,
)
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.results import (
    RESULTS_FILENAME,
    write_results,
)

_META = EvaluationMeta(
    search_engine=SearchEngineMeta(type="solr", endpoint="http://localhost:8983/solr/testcore/"),
    query_template="template.json",
    top_k=10,
    max_rating_value=4,
    relevance_threshold=2,
)

_QRELS: dict[str, dict[str, int]] = {
    "find cats": {"d1": 4, "d2": 1, "d3": 3},
    "find dogs": {"d4": 2},
}

_RUN: dict[str, dict[str, float]] = {
    "find cats": {"d1": 10.0, "d2": 9.0},
    "find dogs": {},
}

_RESULT = EvaluationResult(
    metrics=["ndcg@10", "map@10"],
    aggregate={"ndcg@10": 0.75, "map@10": 0.60},
    per_query={
        "find cats": {"ndcg@10": 0.81, "map@10": 0.70},
        "find dogs": {"ndcg@10": 0.0, "map@10": 0.0},
    },
)


class TestWriteResults:
    def test_returns_correct_path(self, tmp_path: Path) -> None:
        path = write_results(_RESULT, _RUN, _QRELS, _META, tmp_path)
        assert path == tmp_path / RESULTS_FILENAME

    def test_file_is_valid_json(self, tmp_path: Path) -> None:
        path = write_results(_RESULT, _RUN, _QRELS, _META, tmp_path)
        data = json.loads(path.read_text())
        assert isinstance(data, dict)

    def test_meta_header_present(self, tmp_path: Path) -> None:
        path = write_results(_RESULT, _RUN, _QRELS, _META, tmp_path)
        data = json.loads(path.read_text())
        assert data["search_engine"] == {"type": "solr", "endpoint": "http://localhost:8983/solr/testcore/"}
        assert data["query_template"] == "template.json"
        assert data["top_k"] == 10
        assert data["max_rating_value"] == 4
        assert data["relevance_threshold"] == 2

    def test_num_queries(self, tmp_path: Path) -> None:
        path = write_results(_RESULT, _RUN, _QRELS, _META, tmp_path)
        data = json.loads(path.read_text())
        assert data["num_queries"] == 2

    def test_aggregate_present(self, tmp_path: Path) -> None:
        path = write_results(_RESULT, _RUN, _QRELS, _META, tmp_path)
        data = json.loads(path.read_text())
        assert data["aggregate"] == {"ndcg@10": 0.75, "map@10": 0.60}

    def test_per_query_num_retrieved(self, tmp_path: Path) -> None:
        path = write_results(_RESULT, _RUN, _QRELS, _META, tmp_path)
        data = json.loads(path.read_text())
        # "find cats" run has 2 docs
        assert data["per_query"]["find cats"]["num_retrieved"] == 2.0
        # "find dogs" run is empty
        assert data["per_query"]["find dogs"]["num_retrieved"] == 0.0

    def test_per_query_num_relevant_total(self, tmp_path: Path) -> None:
        # relevance_threshold=2; qrels for "find cats": d1=4, d2=1, d3=3 → 2 relevant (d1, d3)
        path = write_results(_RESULT, _RUN, _QRELS, _META, tmp_path)
        data = json.loads(path.read_text())
        assert data["per_query"]["find cats"]["num_relevant_total"] == 2.0
        # "find dogs": d4=2 → 1 relevant
        assert data["per_query"]["find dogs"]["num_relevant_total"] == 1.0

    def test_per_query_metrics_preserved(self, tmp_path: Path) -> None:
        path = write_results(_RESULT, _RUN, _QRELS, _META, tmp_path)
        data = json.loads(path.read_text())
        assert data["per_query"]["find cats"]["ndcg@10"] == 0.81
        assert data["per_query"]["find cats"]["map@10"] == 0.70

    def test_output_directory_created_when_missing(self, tmp_path: Path) -> None:
        dest = tmp_path / "nested" / "output"
        assert not dest.exists()
        write_results(_RESULT, _RUN, _QRELS, _META, dest)
        assert dest.is_dir()
        assert (dest / RESULTS_FILENAME).exists()

    def test_json_is_indented(self, tmp_path: Path) -> None:
        path = write_results(_RESULT, _RUN, _QRELS, _META, tmp_path)
        raw = path.read_text()
        assert "\n  " in raw  # indent=2 produces two-space indentation
