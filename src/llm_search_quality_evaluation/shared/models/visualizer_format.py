from pydantic import BaseModel

from llm_search_quality_evaluation.shared.models import Query, Document, Rating


class Visualizer(BaseModel):
    """
    Represents the object format for the dataset-generator visualizer.
    """
    queries: list[Query]
    documents: list[Document]
    ratings: list[Rating]
    max_rating_value: int
