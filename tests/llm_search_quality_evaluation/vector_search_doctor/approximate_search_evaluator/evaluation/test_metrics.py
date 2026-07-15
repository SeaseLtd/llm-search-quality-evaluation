import pytest

from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.metrics import (
    DEFAULT_METRICS,
    evaluate_metrics,
    is_supported_metric,
    relevance_threshold,
)


class TestRelevanceThreshold:
    @pytest.mark.parametrize(
        "max_val,expected",
        [(1, 1), (2, 1), (3, 2), (4, 2), (5, 3)],
    )
    def test_known_values(self, max_val: int, expected: int) -> None:
        assert relevance_threshold(max_val) == expected

    def test_zero_raises(self) -> None:
        with pytest.raises(ValueError):
            relevance_threshold(0)

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError):
            relevance_threshold(-1)


class TestIsSupportedMetric:
    @pytest.mark.parametrize(
        "metric",
        ["ndcg@10", "map@5", "mrr@10", "precision@10", "recall@10", "hits@5"],
    )
    def test_at_k_metrics_accepted(self, metric: str) -> None:
        assert is_supported_metric(metric) is True

    def test_rbp_with_persistence_accepted(self) -> None:
        assert is_supported_metric("rbp.95") is True

    @pytest.mark.parametrize("metric", ["bpref", "r_precision"])
    def test_bare_metrics_accepted(self, metric: str) -> None:
        assert is_supported_metric(metric) is True

    @pytest.mark.parametrize("metric", ["foo@10", "bar"])
    def test_unknown_prefix_rejected(self, metric: str) -> None:
        assert is_supported_metric(metric) is False

    def test_wrong_separator_rejected(self) -> None:
        assert is_supported_metric("ndcg-10") is False


class TestEvaluateMetrics:
    @pytest.fixture
    def perfect_ranking(self) -> tuple[dict, dict]:
        qrels = {
            "q1": {"doc1": 1, "doc2": 0, "doc3": 1},
            "q2": {"doc4": 1, "doc5": 1, "doc6": 0},
        }
        run = {
            "q1": {"doc1": 3, "doc3": 2, "doc2": 1},
            "q2": {"doc4": 3, "doc5": 2, "doc6": 1},
        }
        return qrels, run

    def test_perfect_ranking_ndcg(self, perfect_ranking: tuple) -> None:
        qrels, run = perfect_ranking
        result = evaluate_metrics(qrels, run, ["ndcg@10"], relevance_threshold=1)
        assert result.aggregate["ndcg@10"] == pytest.approx(1.0)

    def test_perfect_ranking_precision(self, perfect_ranking: tuple) -> None:
        qrels, run = perfect_ranking
        result = evaluate_metrics(qrels, run, ["precision@3"], relevance_threshold=1)
        # 2 relevant in top-3: precision@3 = 2/3
        assert result.aggregate["precision@3"] == pytest.approx(2 / 3, abs=1e-4)

    def test_known_ndcg_value(self) -> None:
        # Single query: rel docs at positions 1 and 3 (scores 2.0 and 1.0)
        # Ideal order: both relevant first. DCG = 1/log2(2) + 1/log2(4) = 1 + 0.5 = 1.5
        # Actual order same as ideal -> nDCG = 1.0
        qrels = {"q1": {"doc1": 1, "doc2": 1}}
        run = {"q1": {"doc1": 2, "doc2": 1}}
        result = evaluate_metrics(qrels, run, ["ndcg@10"], relevance_threshold=1)
        assert result.aggregate["ndcg@10"] == pytest.approx(1.0)

    def test_per_query_keys_match_qrels_keys(self, perfect_ranking: tuple) -> None:
        qrels, run = perfect_ranking
        result = evaluate_metrics(qrels, run, ["ndcg@10"], relevance_threshold=1)
        assert set(result.per_query.keys()) == set(qrels.keys())

    def test_per_query_missing_query_scores_zero(self) -> None:
        qrels = {"q1": {"doc1": 1}, "q2": {"doc2": 1}}
        # run only has q1; q2 is absent
        run = {"q1": {"doc1": 1}}
        result = evaluate_metrics(qrels, run, ["ndcg@10"], relevance_threshold=1)
        assert "q2" in result.per_query
        assert result.per_query["q2"]["ndcg@10"] == pytest.approx(0.0)

    def test_aggregate_values_are_floats(self, perfect_ranking: tuple) -> None:
        qrels, run = perfect_ranking
        result = evaluate_metrics(qrels, run, ["ndcg@10"], relevance_threshold=1)
        for v in result.aggregate.values():
            assert isinstance(v, float)

    def test_per_query_values_are_floats(self, perfect_ranking: tuple) -> None:
        qrels, run = perfect_ranking
        result = evaluate_metrics(qrels, run, ["ndcg@10"], relevance_threshold=1)
        for query_vals in result.per_query.values():
            for v in query_vals.values():
                assert isinstance(v, float)

    def test_unsupported_metric_raises(self, perfect_ranking: tuple) -> None:
        qrels, run = perfect_ranking
        with pytest.raises(ValueError, match="foo@10"):
            evaluate_metrics(qrels, run, ["foo@10"], relevance_threshold=1)

    def test_empty_qrels_raises(self) -> None:
        with pytest.raises(ValueError, match="qrels is empty"):
            evaluate_metrics({}, {}, ["ndcg@10"], relevance_threshold=1)

    def test_metrics_field_matches_input(self, perfect_ranking: tuple) -> None:
        qrels, run = perfect_ranking
        metrics = ["ndcg@10", "map@10"]
        result = evaluate_metrics(qrels, run, metrics, relevance_threshold=1)
        assert result.metrics == metrics

    def test_default_metrics_all_supported(self) -> None:
        for m in DEFAULT_METRICS:
            assert is_supported_metric(m), f"DEFAULT_METRICS entry '{m}' not supported"
