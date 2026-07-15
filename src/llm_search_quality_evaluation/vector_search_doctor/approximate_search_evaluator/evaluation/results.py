import json
import logging
from pathlib import Path

from .models import EvaluationMeta, EvaluationResult

log = logging.getLogger(__name__)

RESULTS_FILENAME = "evaluation_results.json"


def write_results(
    result: EvaluationResult,
    run: dict[str, dict[str, float]],
    qrels: dict[str, dict[str, int]],
    meta: EvaluationMeta,
    output_destination: Path,
) -> Path:
    """Write the results JSON and return the written file path."""
    output_destination.mkdir(parents=True, exist_ok=True)

    per_query: dict[str, dict[str, float]] = {}
    for text, metrics in result.per_query.items():
        num_retrieved = float(len(run.get(text, {})))
        num_relevant_total = float(
            sum(1 for s in qrels.get(text, {}).values() if s >= meta.relevance_threshold)
        )
        per_query[text] = {
            **metrics,
            "num_retrieved": num_retrieved,
            "num_relevant_total": num_relevant_total,
        }

    output = {
        **meta.model_dump(),
        "num_queries": len(result.per_query),
        "metrics": result.metrics,
        "aggregate": result.aggregate,
        "per_query": per_query,
    }

    output_path = output_destination / RESULTS_FILENAME
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    log.info("Evaluation results written to %s", output_path)
    return output_path
