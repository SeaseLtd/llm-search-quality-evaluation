import uuid

from app.models.document import DocumentBase, Document


# Properties to receive on document creation
class DocumentCreate(DocumentBase):
    pass

class DocumentPublic(DocumentBase):
    document_id: uuid.UUID

    def __init__(self, document: Document):
        super().__init__(
            document_id=document.document_id,
        )
