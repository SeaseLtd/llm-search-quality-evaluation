#!/usr/bin/env python3
"""
MTEB execution pipeline entrypoint for Module 2.

- Loads MTEB tasks in-memory (no export to disk required).
- Evaluates either Retrieval or Re-ranking using a cached-embedding wrapper.
- Compute MTEB Leaderboard model comparison and add them to the custom task result file.
- Writes embeddings to disk only after evaluation (optional but kept as before).
- Dataset/split/model/task are driven by Config.
"""

from __future__ import annotations

import argparse
import logging
import time
import json
from pathlib import Path
from typing import Any

import mteb
from mteb.models.cache_wrapper import CachedEmbeddingWrapper
from mteb.overview import TASKS_REGISTRY

from llm_search_quality_evaluation.vector_search_doctor.embedding_model_evaluator.config import Config
from llm_search_quality_evaluation.vector_search_doctor.embedding_model_evaluator.custom_mteb_tasks import (  # noqa: F401 (tasks must be imported to register)
    CustomRerankingTask,
    CustomRetrievalTask,
)
from llm_search_quality_evaluation.vector_search_doctor.embedding_model_evaluator.embedding_writer import EmbeddingWriter
from llm_search_quality_evaluation.vector_search_doctor.embedding_model_evaluator.constants import TASKS_NAME_MAPPING, CACHE_PATH
from llm_search_quality_evaluation.shared.logger import setup_logging  # type: ignore[import]

log = logging.getLogger(__name__)

CACHE_PATH.mkdir(parents=True, exist_ok=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embedding Model Evaluator (MTEB, in-memory).")
    parser.add_argument(
        "--config",
        type=str,
        help='Config file path to use for the application [default: '
             '"examples/configs/vector_search_doctor/embedding_model_evaluator/embedding_model_evaluator_config.yaml"]',
        required=False,
        default="examples/configs/vector_search_doctor/embedding_model_evaluator/embedding_model_evaluator_config.yaml",
    )
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Activate debug mode for logging [default: False]')

    return parser.parse_args()


def _build_task(task_name: str, dataset_name: str, split: str) -> Any:
    """
    Instantiate the requested task from TASKS_REGISTRY and inject dataset/split.
    We try constructor kwargs first; if not supported, we set attributes (best-effort).
    This keeps us decoupled from CustomTask signatures while remaining robust.
    """

    task_cls = TASKS_REGISTRY[task_name]

    # Try the flexible constructor path.
    try:
        task = task_cls(dataset_names=[dataset_name], eval_splits=[split])
        return task
    except TypeError:
        # Fallback: default constructor + attribute injection
        task = task_cls()
        if hasattr(task, "dataset_names"):
            setattr(task, "dataset_names", [dataset_name])
        if hasattr(task, "eval_splits"):
            setattr(task, "eval_splits", [split])
        return task


def _add_mteb_leaderboard_comparison_metrics(file_path: Path, mteb_comparison_metrics: dict) -> None:
    """
    1. Read from custom task result json file (file_path)
    2. Get custom task main_score
    3. Model main_score diffs : custom task main_score vs MTEB Leaderboard model avg_main_score
    4. Raise a warning if user model is significantly worse, 20% performance gap
    5. Add mteb comparison metrics to the file
    """

    # 1. Read from custom task result json file (file_path)
    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    # 2. Get user model's computed main_score on custom dataset
    user_model_main_score = data["scores"]["test"][0]["main_score"]

    # Convert to percentage
    user_model_main_score *= 100

    # 3. Model main_score diffs : custom task main_score vs MTEB Leaderboard model avg_main_score
    top_avg_main_score = mteb_comparison_metrics["top_model_avg_main_score"]
    top_model_name = mteb_comparison_metrics["top_model"]
    user_model_name = mteb_comparison_metrics["user_model"]
    user_model_avg_main_score = mteb_comparison_metrics["user_model_mteb_avg_main_score"]

    model_main_score_diff = (f"Your model's main_score on custom task main_score={user_model_main_score:.2f} vs. "
                             f"MTEB leaderboard shown avg_main_score={user_model_avg_main_score:.2f}")
    mteb_comparison_metrics["user_model_custom_task_main_score"] = user_model_main_score
    mteb_comparison_metrics["model_main_score_diff"] = model_main_score_diff

    # 4. Raise a warning if user model is significantly worse, 20% performance gap
    threshold_percent = 20.0
    if top_avg_main_score > 0:
        diff = top_avg_main_score - user_model_main_score
        # Calculate how much worse (in %) user model is compared to the top model
        diff_percent = (diff / top_avg_main_score) * 100
        if diff_percent > threshold_percent:
            log.debug(f"Model performance exceeded threshold={threshold_percent}%, warning added to custom task result")
            warning = f"Your model={user_model_name} is {diff_percent:.2f}% worse than the top model={top_model_name}."
            mteb_comparison_metrics["warning"] = warning

    # 5. Add mteb comparison metrics to the file
    data["mteb_leaderboard_model_comparison"] = mteb_comparison_metrics

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        log.debug(f"Added MTEB leaderboard comparison metrics to {file_path}")


def compute_mteb_leaderboard_comparison(model_name: str, task_type: str) -> dict:
    """
    1. Fetch mteb model results from https://github.com/embeddings-benchmark/results
    2. Calculate averages for all models.
    3. Find the top #1 model for the given task based on avg_main_score.
    4. Return user model (model_name), top model avg_main_scores.
    """

    benchmark = mteb.get_benchmark("MTEB(eng, v2)")
    tasks = [t for t in benchmark.tasks if t.metadata.type == task_type]
    # include "mostly complete" tasks for the models, so excluding models which are run on a few tasks
    num_tasks = len(tasks) * 0.7

    # 1. Fetch mteb results from https://github.com/embeddings-benchmark/results into ~/.cache/mteb/results
    all_results = mteb.load_results(tasks=tasks).join_revisions()

    # 2. Calculate averages for all models.
    model_averages = {}  # <model_name, avg_main_score>
    for model_res in all_results.model_results:
        total_score = 0
        count = 0
        for task_obj in tasks:
            task_name = task_obj.metadata.name
            task_result = next((res for res in model_res.task_results if res.task_name == task_name), None)
            if task_result:
                main_score = task_result.get_score()
                if main_score <= 1.0:  # in case if task's main_score is in [0, 1] ratio
                    main_score *= 100
                total_score += main_score
                count += 1
            else:
                pass
        if count >= num_tasks:
            model_averages[model_res.model_name] = float(total_score / count)

    # 3. Find the top #1 model for the given task based on avg_main_score.
    top_model_name: str = "None"
    top_avg_main_score: float = 0.0
    for name, score in model_averages.items():
        if score > top_avg_main_score:
            top_avg_main_score = score
            top_model_name = name

    user_avg_main_score = model_averages.get(model_name, 0.0)

    return {
        "top_model": top_model_name,
        "top_model_avg_main_score": top_avg_main_score,
        "user_model": model_name,
        "user_model_mteb_avg_main_score": user_avg_main_score
    }


def main() -> None:
    args = _parse_args()
    setup_logging(args.verbose)
    config: Config = Config.load(args.config)

    # --- Sanity logs (explicit & helpful) ---
    log.info("MTEB run → task=%s | dataset=%s | split=%s | model=%s",
             config.task_to_evaluate, config.dataset_name, config.split, config.model_id)

    # --- Model + caching wrapper ---
    model = mteb.get_model(config.model_id, trust_remote_code=True)
    task_name = TASKS_NAME_MAPPING.get(config.task_to_evaluate, None)
    if task_name is None:
        log.error("Custom task name is not defined: %s", task_name)
        raise ValueError("Custom task name is not defined.")

    if config.output_dest is None:
        raise ValueError("config.output_dest is not set, default_dir must be `resources`")

    model_name_additional_path = config.model_id.replace("/", "__").replace(" ", "_")
    model_with_cache_path = CACHE_PATH / model_name_additional_path

    log.debug(f"Using embedding cache at {model_with_cache_path}")
    model_with_cache = CachedEmbeddingWrapper(model, cache_path=model_with_cache_path)

    # --- Task instance (in-memory) ---
    try:
        task = _build_task(
            task_name=task_name,
            dataset_name=config.dataset_name,
            split=config.split,
        )
    except Exception as e:
        log.error("Failed to build MTEB task: %s", e)
        raise ValueError("Failed to build MTEB task.")

    # --- MTEB Evaluation ---
    log.info("Starting MTEB evaluation...")
    start = time.time()
    evaluation = mteb.MTEB(tasks=[task])
    evaluation.run(
        model=model_with_cache,
        output_folder=str(config.output_dest),
        overwrite_results=True,
        config=config,
    )

    end = time.time()
    log.info("Finished MTEB evaluation.")
    log.info(f"Time took for MTEB evaluation: {(end - start) / 60:.2f} minutes")

    log.info("Computing MTEB Leaderboard comparison metrics...")

    # task result is in {output_folder} / {model_name} / {model_revision} / {task_name}.json
    task_result_path: Path = (config.output_dest / model_name_additional_path /
                              mteb.get_model_meta(config.model_id).revision / f"{task_name}.json")

    # --- Compute MTEB Leaderboard model comparison and add them to the custom task result file ---
    mteb_comparison_metrics: dict = compute_mteb_leaderboard_comparison(config.model_id,
                                                                        config.task_to_evaluate.capitalize())
    _add_mteb_leaderboard_comparison_metrics(task_result_path, mteb_comparison_metrics)

    # --- Write embeddings ---
    writer = EmbeddingWriter(
        corpus_path=config.corpus_path,
        queries_path=config.queries_path,
        cached=model_with_cache,
        cache_path=model_with_cache_path,
        task_name=task_name,
        batch_size=256,
    )
    writer.write(config.embeddings_dest)


if __name__ == "__main__":
    main()
