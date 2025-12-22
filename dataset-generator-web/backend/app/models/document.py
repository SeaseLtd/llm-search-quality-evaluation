import uuid

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, JSON


# Shared properties
class DocumentBase(SQLModel):
    fields: str = Field(min_length=1, sa_column=Column(JSON))


# Properties to receive on case creation
class DocumentCreate(DocumentBase):
    pass


# Database model, database table inferred from class name
class Document(DocumentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class DocumentPublic(DocumentBase):
    id: uuid.UUID


class DocumentsPublic(SQLModel):
    data: list[DocumentPublic]
    count: int
