import ranx

from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.models import EvaluationResult

DEFAULT_METRICS: list[str] = [
    "ndcg@10",
    "map@10",
    "mrr@10",
    "precision@10",
    "recall@10",
]

SUPPORTED_METRIC_PREFIXES: set[str] = {
    "hits",
    "hit_rate",
    "precision",
    "recall",
    "f1",
    "mrr",
    "map",
    "dcg",
    "dcg_burges",
    "ndcg",
    "ndcg_burges",
    "r_precision",
    "bpref",
    "rbp",
}


def is_supported_metric(metric: str) -> bool:
    """True if `metric` has a supported ranx prefix."""
    # strip @k suffix (e.g. "ndcg@10" -> "ndcg")
    base = metric.split("@")[0]
    # strip .p suffix (e.g. "rbp.95" -> "rbp")
    base = base.split(".")[0]
    return base in SUPPORTED_METRIC_PREFIXES


def relevance_threshold(max_rating_value: int) -> int:
    """Minimum rating to count as relevant for binary metrics.

    Returns ceil(max_rating_value / 2) == (max_rating_value + 1) // 2.
    Raises ValueError if max_rating_value < 1.
    """
    if max_rating_value < 1:
        raise ValueError(f"max_rating_value must be >= 1, got {max_rating_value}")
    return (max_rating_value + 1) // 2


def evaluate_metrics(
    qrels: dict[str, dict[str, int]],   # query_text -> {doc_id: relevance_score}
    run: dict[str, dict[str, int]],     # query_text -> {doc_id: rank_score} (position-derived: score = top_k - position)
    metrics: list[str],                 # e.g. ["ndcg@10", "map@10"]
    relevance_threshold: int,           # min relevance to count a doc as relevant for binary metrics
) -> EvaluationResult:
    """Compute `metrics` for `run` against `qrels` using ranx."""
    if not qrels:
        raise ValueError("qrels is empty")

    unsupported = [m for m in metrics if not is_supported_metric(m)]
    if unsupported:
        raise ValueError(f"Unsupported metric(s): {unsupported}")

    qrels_obj = ranx.Qrels.from_dict(qrels)
    qrels_obj.set_relevance_level(relevance_threshold)
    run_obj = ranx.Run.from_dict(run)

    aggregate_raw = ranx.evaluate(qrels_obj, run_obj, metrics, make_comparable=True)
    if isinstance(aggregate_raw, float):
        aggregate_raw = {metrics[0]: aggregate_raw}
    aggregate = {k: float(v) for k, v in aggregate_raw.items()}

    per_query_raw = ranx.evaluate(
        qrels_obj, run_obj, metrics, return_mean=False, make_comparable=True
    )
    if not isinstance(per_query_raw, dict):
        per_query_raw = {metrics[0]: per_query_raw}

    query_keys = sorted(qrels.keys())
    per_query: dict[str, dict[str, float]] = {q: {} for q in query_keys}
    for metric_name, values in per_query_raw.items():
        for query_key, value in zip(query_keys, values):
            per_query[query_key][metric_name] = float(value)

    return EvaluationResult(metrics=metrics, aggregate=aggregate, per_query=per_query)
