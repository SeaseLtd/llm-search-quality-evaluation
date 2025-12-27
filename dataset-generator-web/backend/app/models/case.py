import uuid

from sqlmodel import Field, Relationship, SQLModel

from app.models.user import User

# Shared properties
class CaseBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    max_rating_value: int = Field(default=3, gt=0)
    document_title_field_name: str = Field(default="title", max_length=32)


# Database model, database table inferred from class name
class Case(CaseBase, table=True):
    case_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.user_id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="cases")
    queries: list["Query"] = Relationship(back_populates="case", cascade_delete=True)
