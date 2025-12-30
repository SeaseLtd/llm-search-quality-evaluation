import uuid
from sqlmodel import Field

from app.models.document import DocumentBase, Document


# Properties to receive on document creation
class DocumentCreate(DocumentBase):
    document_id: str = Field(default_factory=uuid.uuid4)


class DocumentPublic(DocumentBase):
    case_id: uuid.UUID
    document_id: str

    def __init__(self, document: Document):
        super().__init__(
            document_id=document.document_id,
        )
