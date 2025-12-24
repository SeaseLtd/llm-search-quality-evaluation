import uuid

from sqlmodel import Field, Relationship, SQLModel

from app.models.query import Query
from app.models.document import Document


# Shared properties
class RatingBase(SQLModel):
    llm_rating: int = Field(nullable=True, gt=0)
    user_rating: int = Field(nullable=True, gt=0)


# Properties to receive on rating creation
class RatingCreate(RatingBase):
    query_id: uuid.UUID
    document_id: uuid.UUID


# Database model, database table inferred from class name
class Rating(RatingBase, table=True):
    query_id: uuid.UUID = Field(foreign_key="query.id", primary_key=True, nullable=False, ondelete="CASCADE")
    document_id: uuid.UUID = Field(foreign_key="document.id", primary_key=True, nullable=False, ondelete="CASCADE")
    query: Query = Relationship(back_populates="ratings")
    document: Document = Relationship(back_populates="ratings")

class RatingPublic(RatingBase):
    query_id: uuid.UUID
    document_id: uuid.UUID
