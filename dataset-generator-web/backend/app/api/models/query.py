import typing
import uuid
from sqlmodel import Field

import app
from app.api.models.rating import RatingDetailed
from app.models.query import QueryBase, Query


# Properties to receive on query creation
class QueryCreate(QueryBase):
    query_id: str = Field(default_factory=uuid.uuid4)


class QueryPublic(QueryBase):
    query_id: str
    case_id: uuid.UUID
    ratings: typing.Optional[list[RatingDetailed]]

    def __init__(self, query: Query):
        super().__init__(
            query_id=query.query_id,
            query=query.query,
            case_id=query.case_id,
            ratings=[
                RatingDetailed.model_validate(rating)
                for rating in sorted(query.ratings, key=lambda r: r.position)
            ] if query.ratings else None,
        )

