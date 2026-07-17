from pathlib import Path

import pytest
from pydantic import HttpUrl
from pydantic_core import ValidationError

from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator import Config
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.metrics import (
    DEFAULT_METRICS,
)


# --------------- solr ---------------

class TestSolrConfig:
    def test_good_config_solr_all_fields(self, resource_folder: Path) -> None:
        config = Config.load(resource_folder / "good_config_solr.yaml")

        assert config.query_template == Path("tests/resources/template_solr.json")
        assert config.search_engine_type == "solr"
        assert config.collection_name == "testcore"
        assert config.search_engine_url == HttpUrl("http://localhost:8983/solr/")
        assert config.id_field == "new_id"
        assert config.query_placeholder == "$query_placeholder"
        assert config.evaluation_dataset_path == Path(
            "tests/resources/approximate_search_evaluator/evaluation_dataset.json.gz"
        )
        assert config.embeddings_file == Path(
            "tests/resources/approximate_search_evaluator/queries_embeddings.jsonl"
        )
        assert config.output_destination == Path("solr_resources")
        assert config.doc_fields == ["title", "body"]
        assert config.top_k == 20
        assert config.metrics == ["ndcg@10", "map@10"]

    def test_solr_defaults(self, resource_folder: Path) -> None:
        config = Config.load(resource_folder / "missing_optional_solr.yaml")

        assert config.id_field == "id"
        assert config.query_placeholder == "$query"
        assert config.embeddings_file is None
        assert config.output_destination == Path("resources")
        assert config.doc_fields == []
        assert config.top_k == 10
        assert config.metrics == list(DEFAULT_METRICS)

    def test_solr_collection_endpoint(self, resource_folder: Path) -> None:
        config = Config.load(resource_folder / "missing_optional_solr.yaml")
        endpoint = config.search_engine_collection_endpoint
        assert str(endpoint) == "http://localhost:8983/solr/testcore/"


# --------------- elasticsearch ---------------

class TestElasticsearchConfig:
    def test_good_config_elasticsearch_all_fields(self, resource_folder: Path) -> None:
        config = Config.load(resource_folder / "good_config_elasticsearch.yaml")

        assert config.query_template == Path("tests/resources/template_elasticsearch.json")
        assert config.search_engine_type == "elasticsearch"
        assert config.collection_name == "testcore"
        assert config.search_engine_url == HttpUrl("http://localhost:9200/")
        assert config.id_field == "new_id"
        assert config.evaluation_dataset_path == Path(
            "tests/resources/approximate_search_evaluator/evaluation_dataset.json.gz"
        )
        assert config.top_k == 10
        assert config.metrics == ["ndcg@10", "mrr@10"]

    def test_elasticsearch_default_id_field(self, resource_folder: Path) -> None:
        config = Config.load(resource_folder / "missing_optional_elasticsearch.yaml")
        assert config.id_field == "_id"

    def test_elasticsearch_collection_endpoint(self, resource_folder: Path) -> None:
        config = Config.load(resource_folder / "missing_optional_elasticsearch.yaml")
        endpoint = config.search_engine_collection_endpoint
        assert str(endpoint) == "http://localhost:9200/testcore/"


# --------------- opensearch ---------------

class TestOpensearchConfig:
    def test_good_config_opensearch(self, resource_folder: Path) -> None:
        config = Config.load(resource_folder / "good_config_opensearch.yaml")
        assert config.search_engine_type == "opensearch"
        assert config.id_field == "id"

    def test_opensearch_collection_endpoint(self, resource_folder: Path) -> None:
        config = Config.load(resource_folder / "good_config_opensearch.yaml")
        endpoint = config.search_engine_collection_endpoint
        assert str(endpoint) == "http://localhost:9200/testcore/"


# --------------- vespa rejected ---------------

class TestVespaRejected:
    def test_vespa_engine_type_rejected(self, resource_folder: Path, tmp_path: Path) -> None:
        config_file = tmp_path / "vespa_config.yaml"
        config_file.write_text(
            "query_template: tests/resources/template_solr.json\n"
            "search_engine_type: vespa\n"
            "collection_name: testcore\n"
            "search_engine_url: http://localhost:8080/\n"
            f"evaluation_dataset_path: {resource_folder}/evaluation_dataset.json.gz\n"
        )
        with pytest.raises(ValidationError):
            Config.load(config_file)


# --------------- missing required fields ---------------

class TestMissingRequiredFields:
    @pytest.mark.parametrize("file_name", [
        "missing_query_template.yaml",
        "missing_search_engine_type.yaml",
        "missing_collection_name.yaml",
        "missing_search_engine_url.yaml",
        "missing_evaluation_dataset_path.yaml",
    ])
    def test_missing_required_field_raises(self, resource_folder: Path, file_name: str) -> None:
        with pytest.raises(ValidationError):
            Config.load(resource_folder / file_name)

    def test_nonexistent_config_file_raises(self, resource_folder: Path) -> None:
        with pytest.raises(FileNotFoundError):
            Config.load(resource_folder / "file_does_not_exist.yaml")

    def test_nonexistent_evaluation_dataset_path_raises(
        self, resource_folder: Path, tmp_path: Path
    ) -> None:
        config_file = tmp_path / "bad_dataset.yaml"
        config_file.write_text(
            "query_template: tests/resources/template_solr.json\n"
            "search_engine_type: solr\n"
            "collection_name: testcore\n"
            "search_engine_url: http://localhost:8983/solr/\n"
            "evaluation_dataset_path: /nonexistent/path/evaluation_dataset.json.gz\n"
        )
        with pytest.raises(ValidationError):
            Config.load(config_file)


# --------------- metrics validation ---------------

class TestMetricsValidation:
    def test_metrics_default_is_default_metrics(self, resource_folder: Path) -> None:
        config = Config.load(resource_folder / "missing_optional_solr.yaml")
        assert config.metrics == list(DEFAULT_METRICS)

    def test_unsupported_metric_raises(self, resource_folder: Path, tmp_path: Path) -> None:
        config_file = tmp_path / "bad_metrics.yaml"
        config_file.write_text(
            "query_template: tests/resources/template_solr.json\n"
            "search_engine_type: solr\n"
            "collection_name: testcore\n"
            "search_engine_url: http://localhost:8983/solr/\n"
            f"evaluation_dataset_path: {resource_folder}/evaluation_dataset.json.gz\n"
            "metrics: [ndcg@10, not_a_metric@5]\n"
        )
        with pytest.raises(ValidationError):
            Config.load(config_file)

    def test_empty_metrics_raises(self, resource_folder: Path, tmp_path: Path) -> None:
        config_file = tmp_path / "empty_metrics.yaml"
        config_file.write_text(
            "query_template: tests/resources/template_solr.json\n"
            "search_engine_type: solr\n"
            "collection_name: testcore\n"
            "search_engine_url: http://localhost:8983/solr/\n"
            f"evaluation_dataset_path: {resource_folder}/evaluation_dataset.json.gz\n"
            "metrics: []\n"
        )
        with pytest.raises(ValidationError):
            Config.load(config_file)


# --------------- top_k validation ---------------

class TestTopKValidation:
    def test_top_k_zero_raises(self, resource_folder: Path, tmp_path: Path) -> None:
        config_file = tmp_path / "bad_topk.yaml"
        config_file.write_text(
            "query_template: tests/resources/template_solr.json\n"
            "search_engine_type: solr\n"
            "collection_name: testcore\n"
            "search_engine_url: http://localhost:8983/solr/\n"
            f"evaluation_dataset_path: {resource_folder}/evaluation_dataset.json.gz\n"
            "top_k: 0\n"
        )
        with pytest.raises(ValidationError):
            Config.load(config_file)

    def test_top_k_negative_raises(self, resource_folder: Path, tmp_path: Path) -> None:
        config_file = tmp_path / "neg_topk.yaml"
        config_file.write_text(
            "query_template: tests/resources/template_solr.json\n"
            "search_engine_type: solr\n"
            "collection_name: testcore\n"
            "search_engine_url: http://localhost:8983/solr/\n"
            f"evaluation_dataset_path: {resource_folder}/evaluation_dataset.json.gz\n"
            "top_k: -1\n"
        )
        with pytest.raises(ValidationError):
            Config.load(config_file)
