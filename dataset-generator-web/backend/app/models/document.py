import uuid

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, JSON


# Shared properties
class DocumentBase(SQLModel):
    fields: dict[str, str] = Field(default={}, sa_column=Column(JSON))


# Properties to receive on document creation
class DocumentCreate(DocumentBase):
    pass


# Database model, database table inferred from class name
class Document(DocumentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ratings: list["Rating"] = Relationship(back_populates="document", cascade_delete=True)


class DocumentPublic(DocumentBase):
    id: uuid.UUID


# Document with rating for nested responses
class DocumentWithRating(DocumentPublic):
    rating: int
