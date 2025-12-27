import typing
import uuid

from app.api.models.document import DocumentPublic
from app.models.rating import RatingBase, Rating


# Properties to receive on rating creation
class RatingCreate(RatingBase):
    query_id: uuid.UUID
    document_id: uuid.UUID


class RatingDetailed(RatingBase):
    document: DocumentPublic