from pydantic import BaseModel, Field


class SearchEngineMeta(BaseModel):
    type: str
    endpoint: str


class EvaluationMeta(BaseModel):
    """Self-describing header for an evaluation run (built by the orchestrator, Task 07)."""

    search_engine: SearchEngineMeta
    query_template: str
    top_k: int
    max_rating_value: int
    relevance_threshold: int


class EvaluationResult(BaseModel):
    """Outcome of an evaluation run, keyed by query text."""

    metrics: list[str]
    aggregate: dict[str, float]
    per_query: dict[str, dict[str, float]]


class QuerySpec(BaseModel):
    """A single query to run against the engine."""

    text: str  # value for the $query placeholder
    extra_placeholders: dict[str, str] = Field(default_factory=dict)
    # e.g. {"$vector": "[0.12, 0.98, ...]"} — populated later by Task 04


class EvaluationInput(BaseModel):
    """Everything needed to run an evaluation, from any input source."""

    qrels: dict[str, dict[str, int]]  # query_text -> {doc_id: relevance}
    query_specs: list[QuerySpec]
    max_rating_value: int  # from the dataset; feeds relevance_threshold()
