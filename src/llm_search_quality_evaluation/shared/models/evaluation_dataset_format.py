from pydantic import BaseModel

from llm_search_quality_evaluation.shared.models import Document, Query, Rating


class EvaluationDataset(BaseModel):
    """
    Self-contained, serializable evaluation dataset produced by the dataset
    generator: the queries, documents and relevance ratings collected in the
    DataStore, plus the maximum rating value.
    """

    queries: list[Query]
    documents: list[Document]
    ratings: list[Rating]
    max_rating_value: int
