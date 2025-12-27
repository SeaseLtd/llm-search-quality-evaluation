import uuid

from sqlmodel import Field, Relationship, SQLModel

# Shared properties
class QueryBase(SQLModel):
    query: str = Field(min_length=1, max_length=255)

# Database model, database table inferred from class name
class Query(QueryBase, table=True):
    query_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    case_id: uuid.UUID = Field(
        foreign_key="case.case_id", nullable=False, ondelete="CASCADE"
    )
    case: "Case" = Relationship(back_populates="queries")
    ratings: list["Rating"] = Relationship(back_populates="query", cascade_delete=True)

