import uuid

from sqlmodel import Field, Relationship, SQLModel

from app.models.case import Case


# Shared properties
class QueryBase(SQLModel):
    query: str = Field(min_length=1, max_length=255)


# Properties to receive on case creation
class QueryCreate(QueryBase):
    pass


# Database model, database table inferred from class name
class Query(QueryBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    case_id: uuid.UUID = Field(
        foreign_key="case.id", nullable=False, ondelete="CASCADE"
    )
    case: Case = Relationship(back_populates="queries")


class QueryPublic(QueryBase):
    id: uuid.UUID
    case_id: uuid.UUID


class QueriesPublic(SQLModel):
    data: list[QueryPublic]
    count: int
