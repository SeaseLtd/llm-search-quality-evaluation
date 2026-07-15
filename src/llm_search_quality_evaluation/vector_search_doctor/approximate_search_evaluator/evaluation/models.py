from pydantic import BaseModel


class EvaluationResult(BaseModel):
    """Outcome of an evaluation run, keyed by query text."""

    metrics: list[str]
    aggregate: dict[str, float]
    per_query: dict[str, dict[str, float]]
