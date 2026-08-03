import json
import logging
from pathlib import Path

import jsonlines

from llm_search_quality_evaluation.shared.models import Query
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.models import (
    QuerySpec,
)

log = logging.getLogger(__name__)

QUERIES_EMBEDDINGS_FILENAME = "queries_embeddings.jsonl"


def load_query_vectors(embeddings_file: Path, queries: list[Query]) -> dict[str, str]:
    """Read queries_embeddings.jsonl and return a mapping query_text -> vector_string."""

    query_id_to_text = {q.id: q.text for q in queries}
    result: dict[str, str] = {}
    with jsonlines.open(embeddings_file) as reader:
        for entry in reader:
            query_id = entry["id"]
            text = query_id_to_text.get(query_id)
            if text is None:
                log.warning("Embedding entry references unknown query_id %r — skipping.", query_id)
                continue
            result[text] = json.dumps(entry["vector"])
    return result


def attach_vectors(
    query_specs: list[QuerySpec],
    text_to_vector: dict[str, str],
    placeholder: str = "$vector",
) -> list[QuerySpec]:
    """Return new QuerySpecs with extra_placeholders[placeholder] set where a vector exists."""
    updated: list[QuerySpec] = []
    for spec in query_specs:
        vector = text_to_vector.get(spec.text)
        if vector is not None:
            new_placeholders = {**spec.extra_placeholders, placeholder: vector}
            updated.append(spec.model_copy(update={"extra_placeholders": new_placeholders}))
        else:
            updated.append(spec)
    return updated


def ensure_placeholder_values(
    query_specs: list[QuerySpec],
    placeholder: str = "$vector",
) -> None:
    """Raise if any query is missing a required placeholder value."""

    missing = [
        spec.text for spec in query_specs if placeholder not in spec.extra_placeholders
    ]
    if not missing:
        return

    preview = ", ".join(repr(text) for text in missing[:5])
    suffix = " ..." if len(missing) > 5 else ""
    raise ValueError(
        f"Missing {placeholder} values for {len(missing)} query(s): {preview}{suffix}"
    )
