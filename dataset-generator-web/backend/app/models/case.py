import uuid

from sqlmodel import Field, Relationship, SQLModel

from app.models.user import User
from app.models.query import QueryPublic


# Shared properties
class CaseBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on case creation
class CaseCreate(CaseBase):
    pass


# Properties to receive on case update
class CaseUpdate(CaseBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Case(CaseBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="cases")
    queries: list["Query"] = Relationship(back_populates="case", cascade_delete=True)


# Properties to return via API, id is always required
class CasePublic(CaseBase):
    id: uuid.UUID
    owner_id: uuid.UUID


# Detailed case view with queries
class CaseDetailed(CasePublic):
    queries: list[QueryPublic]

