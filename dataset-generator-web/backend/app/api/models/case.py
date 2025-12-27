import uuid

from app.api.models.query import QueryPublic
from app.models.case import CaseBase, Case
from pydantic import Field


# Properties to receive on case creation
class CaseCreate(CaseBase):
    pass


# Properties to receive on case update
class CaseUpdate(CaseBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Properties to return via API, id is always required
class CasePublic(CaseBase):
    case_id: uuid.UUID
    owner_id: uuid.UUID


# Detailed case view with queries
class CaseDetailed(CasePublic):
    queries: list[QueryPublic]

    def __init__(self, case: Case):
        super().__init__(
            case_id=case.case_id,
            title=case.title,
            max_rating_value=case.max_rating_value,
            description=case.description,
            owner_id=case.owner_id,
            queries=[QueryPublic.from_orm(query) for query in case.queries],
        )

