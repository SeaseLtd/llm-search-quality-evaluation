import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models.document import Document, DocumentPublic, DocumentCreate
from app.models.message import Message

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=list[DocumentPublic])
def read_documents(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve documents.
    """
    statement = select(Document).offset(skip).limit(limit)
    return session.exec(statement).all()


@router.get("/{id}", response_model=DocumentPublic)
def read_document(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get document by ID.
    """
    document = session.get(Document, id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("/", response_model=DocumentPublic)
def create_document(
    *, session: SessionDep, current_user: CurrentUser, document_in: DocumentCreate
) -> Any:
    """
    Create new document.
    """
    document = Document.model_validate(document_in)
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


@router.put("/{id}", response_model=DocumentPublic)
def update_document(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    document_in: DocumentCreate,
) -> Any:
    """
    Update a document.
    """
    document = session.get(Document, id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    update_dict = document_in.model_dump(exclude_unset=True)
    document.sqlmodel_update(update_dict)
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


@router.delete("/{id}")
def delete_document(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a document.
    """
    document = session.get(Document, id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    session.delete(document)
    session.commit()
    return Message(message="Document deleted successfully")

