
import uuid

from sqlmodel import Field, Relationship, SQLModel


# Shared properties
class RatingBase(SQLModel):
    llm_rating: int = Field(..., gt=0)


# Properties to receive on case creation
class RatingCreate(RatingBase):
    pass


# Database model, database table inferred from class name
class Rating(RatingBase, table=True):
    query_id: uuid.UUID = Field(foreign_key="query.id", primary_key=True, nullable=False, ondelete="CASCADE")
    document_id: uuid.UUID = Field(foreign_key="document.id", primary_key=True, nullable=False, ondelete="CASCADE")


class RatingPublic(RatingBase):
    query_id: uuid.UUID
    document_id: uuid.UUID


class RatingsPublic(SQLModel):
    data: list[RatingPublic]
    count: int
