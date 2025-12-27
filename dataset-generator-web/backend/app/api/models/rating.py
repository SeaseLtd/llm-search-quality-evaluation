import uuid

from app.api.models.document import DocumentPublic
from app.models.rating import RatingBase
from pydantic import BaseModel, Field


# Properties to receive on rating creation
class RatingCreate(RatingBase):
    query_id: uuid.UUID
    document_id: uuid.UUID

class UserRatingUpdate(BaseModel):
    query_id: uuid.UUID
    document_id: uuid.UUID
    user_rating: int = Field(nullable=False, ge=0)

class RatingDetailed(RatingBase):
    document: DocumentPublic
    position: int
