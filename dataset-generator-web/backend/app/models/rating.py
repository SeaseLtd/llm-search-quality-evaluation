import typing
import uuid
import datetime

from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint
from sqlalchemy import event
from sqlalchemy.orm import Mapper
from sqlalchemy.engine import Connection

from app.models.query import Query
from app.models.document import Document


# Shared properties
class RatingBase(SQLModel):
    llm_rating: typing.Optional[int] = Field(nullable=True, ge=0)
    user_rating: typing.Optional[int] = Field(nullable=True, ge=0)
    explanation: typing.Optional[str] = Field(nullable=True, default=None, max_length=1000)

# Database model, database table inferred from class name
class Rating(RatingBase, table=True):
    __table_args__ = (
        UniqueConstraint("query_id", "position", name="uq_rating_query_position"),
    )

    query_id: uuid.UUID = Field(foreign_key="query.query_id", primary_key=True, nullable=False, ondelete="CASCADE")
    document_id: uuid.UUID = Field(foreign_key="document.document_id", primary_key=True, nullable=False, ondelete="CASCADE")
    position: typing.Optional[int] = Field(nullable=True, ge=0)
    query: Query = Relationship(back_populates="ratings")
    document: Document = Relationship(back_populates="ratings")


# Event listeners to update Query.updated_at when Rating changes
@event.listens_for(Rating, 'after_insert')
@event.listens_for(Rating, 'after_update')
@event.listens_for(Rating, 'after_delete')
def update_query_timestamp_from_rating(mapper: Mapper, connection: Connection, target: Rating) -> None:
    """Update the parent Query's updated_at when a Rating is modified"""
    connection.execute(
        Query.__table__.update().
        where(Query.query_id == target.query_id).
        values(updated_at=datetime.datetime.now(datetime.timezone.utc))
    )


