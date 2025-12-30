import uuid

from app.api.models.document import DocumentPublic
from app.models.rating import RatingBase
from pydantic import BaseModel, Field


# Properties to receive on rating creation
class RatingCreate(RatingBase):
    case_id: uuid.UUID
    query_id: str
    document_id: str

class UserRatingUpdate(BaseModel):
    user_rating: int = Field(nullable=False, ge=0)

class RatingDetailed(RatingBase):
    document: DocumentPublic
    position: int
