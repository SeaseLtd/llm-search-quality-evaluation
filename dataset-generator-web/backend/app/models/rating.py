import typing
import uuid

from sqlmodel import Field, Relationship, SQLModel

from app.models.query import Query
from app.models.document import Document


# Shared properties
class RatingBase(SQLModel):
    llm_rating: typing.Optional[int] = Field(nullable=True, ge=0)
    user_rating: typing.Optional[int] = Field(nullable=True, ge=0)
    explanation: typing.Optional[str] = Field(default=None, max_length=1000)

# Database model, database table inferred from class name
class Rating(RatingBase, table=True):
    query_id: uuid.UUID = Field(foreign_key="query.query_id", primary_key=True, nullable=False, ondelete="CASCADE")
    document_id: uuid.UUID = Field(foreign_key="document.document_id", primary_key=True, nullable=False, ondelete="CASCADE")
    query: Query = Relationship(back_populates="ratings")
    document: Document = Relationship(back_populates="ratings")

