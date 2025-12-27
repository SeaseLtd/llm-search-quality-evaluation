import typing
import uuid

from app.api.models.rating import RatingDetailed
from app.models.query import QueryBase, Query


# Properties to receive on query creation
class QueryCreate(QueryBase):
    pass

class QueryPublic(QueryBase):
    query_id: uuid.UUID
    case_id: uuid.UUID
    ratings: typing.Optional[list[RatingDetailed]]

    def __init__(self, query: Query):
        super().__init__(
            query_id=query.query_id,
            query=query.query,
            case_id=query.case_id,
            ratings=[
                RatingDetailed.model_validate(rating)
                for rating in query.ratings
            ] if query.ratings else None,
        )

