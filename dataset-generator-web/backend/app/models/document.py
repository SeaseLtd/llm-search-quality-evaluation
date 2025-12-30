import uuid
from typing import Any

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, JSON


# Shared properties
class DocumentBase(SQLModel):
    fields: dict[str, Any] = Field(default={}, sa_column=Column(JSON))


# Database model, database table inferred from class name
class Document(DocumentBase, table=True):
    document_id: str = Field(primary_key=True)
    case_id: uuid.UUID = Field(primary_key=True, nullable=False, foreign_key="case.case_id", ondelete="CASCADE")

    case: "Case" = Relationship(back_populates="documents")
    ratings: list["Rating"] = Relationship(back_populates="document", cascade_delete=True)
