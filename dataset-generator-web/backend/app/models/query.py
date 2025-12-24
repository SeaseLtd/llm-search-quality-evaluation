import uuid

from sqlmodel import Field, Relationship, SQLModel

from app.models.document import DocumentWithRating


# Shared properties
class QueryBase(SQLModel):
    query: str = Field(min_length=1, max_length=255)


# Properties to receive on query creation
class QueryCreate(QueryBase):
    pass


# Database model, database table inferred from class name
class Query(QueryBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    case_id: uuid.UUID = Field(
        foreign_key="case.id", nullable=False, ondelete="CASCADE"
    )
    case: "Case" = Relationship(back_populates="queries")
    ratings: list["Rating"] = Relationship(back_populates="query", cascade_delete=True)


class QueryPublic(QueryBase):
    id: uuid.UUID
    case_id: uuid.UUID
    documents: list[DocumentWithRating]

