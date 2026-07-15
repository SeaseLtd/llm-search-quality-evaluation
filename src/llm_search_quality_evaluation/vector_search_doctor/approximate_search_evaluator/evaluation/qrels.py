import logging

from llm_search_quality_evaluation.shared.models.evaluation_dataset_format import (
    EvaluationDataset,
)
from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.models import (
    EvaluationInput,
    QuerySpec,
)

log = logging.getLogger(__name__)


def build_input_from_evaluation_dataset(dataset: EvaluationDataset) -> EvaluationInput:
    """Build qrels + query specs + max_rating_value from an evaluation dataset."""
    query_id_to_text: dict[str, str] = {}
    seen_texts: dict[str, str] = {}  # text -> first query_id that used it
    for query in dataset.queries:
        if query.text in seen_texts:
            log.warning(
                "Query text %r shared by query_id %r and %r; "
                "their judgements will be merged into a single qrels entry.",
                query.text,
                seen_texts[query.text],
                query.id,
            )
        else:
            seen_texts[query.text] = query.id
        query_id_to_text[query.id] = query.text

    qrels: dict[str, dict[str, int]] = {}
    for rating in dataset.ratings:
        text = query_id_to_text.get(rating.query_id)
        if text is None:
            log.warning(
                "Rating references unknown query_id %r — skipping.", rating.query_id
            )
            continue
        if text not in qrels:
            qrels[text] = {}
        qrels[text][rating.doc_id] = int(rating.score)

    query_specs = [QuerySpec(text=text) for text in qrels]

    return EvaluationInput(
        qrels=qrels,
        query_specs=query_specs,
        max_rating_value=dataset.max_rating_value,
    )
