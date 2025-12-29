import uuid
from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import event
from sqlalchemy.orm import Mapper
from sqlalchemy.engine import Connection

# Shared properties
class QueryBase(SQLModel):
    query: str = Field(min_length=1, max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs = {"onupdate": lambda: datetime.now(timezone.utc)},
        nullable=False,
    )


# Database model, database table inferred from class name
class Query(QueryBase, table=True):
    query_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    case_id: uuid.UUID = Field(
        foreign_key="case.case_id", nullable=False, ondelete="CASCADE"
    )
    case: "Case" = Relationship(back_populates="queries")
    ratings: list["Rating"] = Relationship(back_populates="query", cascade_delete=True)
