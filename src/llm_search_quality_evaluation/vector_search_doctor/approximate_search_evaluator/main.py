"""
Approximate Search Evaluator.

Loads an evaluation dataset (evaluation_dataset.json.gz), runs each query against the
configured search engine, computes IR metrics via ranx, and writes evaluation_results.json.
"""
import argparse
import logging
import sys

from llm_search_quality_evaluation.shared.logger import setup_logging
from llm_search_quality_evaluation.shared.models.evaluation_dataset_format import EvaluationDataset
from llm_search_quality_evaluation.shared.search_engines import SearchEngineFactory
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.config import Config
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.embeddings import (
    attach_vectors,
    ensure_placeholder_values,
    load_query_vectors,
)
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.metrics import (
    evaluate_metrics,
    relevance_threshold,
)
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.models import (
    EvaluationMeta,
    SearchEngineMeta,
)
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.qrels import (
    build_input_from_evaluation_dataset,
)
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.results import (
    write_results,
)
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.run import (
    build_run,
)

log = logging.getLogger(__name__)
VECTOR_PLACEHOLDER = "$vector"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse arguments for CLI.")

    parser.add_argument(
        "--config",
        type=str,
        help='Config file path to use for the application [default: '
             '"examples/configs/vector_search_doctor/approximate_search_evaluator/approximate_search_evaluator_config.yaml"]',
        required=False,
        default="examples/configs/vector_search_doctor/approximate_search_evaluator/approximate_search_evaluator_config.yaml",
    )

    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Activate debug mode for logging [default: False]")

    return parser.parse_args()


def main() -> None:
    """Run the approximate search evaluation pipeline."""
    args = _parse_args()
    setup_logging(args.verbose)
    config: Config = Config.load(args.config)

    search_engine = SearchEngineFactory.build(
        search_engine_type=config.search_engine_type,
        endpoint=config.search_engine_collection_endpoint,
    )

    dataset: EvaluationDataset = EvaluationDataset.load(config.evaluation_dataset_path)
    eval_input = build_input_from_evaluation_dataset(dataset)

    if not eval_input.query_specs:
        log.error("No queries found in the evaluation dataset. Aborting.")
        sys.exit(1)

    if config.embeddings_file is not None:
        vectors = load_query_vectors(config.embeddings_file, dataset.queries)
        eval_input.query_specs = attach_vectors(eval_input.query_specs, vectors)
    elif VECTOR_PLACEHOLDER in config.query_template.read_text():
        raise ValueError(
            f"Query template {config.query_template} requires {VECTOR_PLACEHOLDER}, "
            "but embeddings_file is not set."
        )
    else:
        log.warning(
            "No embeddings_file set; '$vector' placeholders (if any) won't be filled."
        )

    if VECTOR_PLACEHOLDER in config.query_template.read_text():
        ensure_placeholder_values(eval_input.query_specs, VECTOR_PLACEHOLDER)

    run = build_run(
        search_engine, config.query_template, eval_input.query_specs, config.doc_fields, config.top_k
    )

    threshold = relevance_threshold(eval_input.max_rating_value)
    result = evaluate_metrics(eval_input.qrels, run, config.metrics, threshold)

    meta = EvaluationMeta(
        search_engine=SearchEngineMeta(
            type=config.search_engine_type,
            endpoint=str(config.search_engine_collection_endpoint),
        ),
        query_template=config.query_template.name,
        top_k=config.top_k,
        max_rating_value=eval_input.max_rating_value,
        relevance_threshold=threshold,
    )
    out_path = write_results(result, run, eval_input.qrels, meta, config.output_destination)

    col_width = max(len(m) for m in result.aggregate) + 2
    metrics_lines = "\n".join(
        f"  {m:<{col_width}}{v:.3f}" for m, v in result.aggregate.items()
    )
    log.info(f"Evaluation completed.\n\nMetrics:\n{metrics_lines}\n\nResults written to:\n  {out_path}")


if __name__ == "__main__":
    main()
