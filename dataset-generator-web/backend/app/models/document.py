import uuid

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, JSON


# Shared properties
class DocumentBase(SQLModel):
    fields: dict[str, str] = Field(default={}, sa_column=Column(JSON))


# Database model, database table inferred from class name
class Document(DocumentBase, table=True):
    document_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ratings: list["Rating"] = Relationship(back_populates="document", cascade_delete=True)
