import logging
from pathlib import Path

from llm_search_quality_evaluation.shared.search_engines import BaseSearchEngine
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.models import (
    QuerySpec,
)

log = logging.getLogger(__name__)


def build_run(
    search_engine: BaseSearchEngine,
    query_template: Path,
    query_specs: list[QuerySpec],
    doc_fields: list[str],
    top_k: int,
) -> dict[str, dict[str, int]]:
    """Run each query against the engine and build the ranx Run."""

    run: dict[str, dict[str, int]] = {}
    for spec in query_specs:
        docs = search_engine.fetch_for_evaluation(
            query_template=query_template,
            doc_fields=doc_fields,
            keyword=spec.text,
            extra_placeholders=spec.extra_placeholders or None,
        )
        docs = docs[:top_k]
        log.debug("Query %r: retrieved %d doc(s).", spec.text, len(docs))
        run[spec.text] = {doc.id: top_k - position for position, doc in enumerate(docs)}
    return run
