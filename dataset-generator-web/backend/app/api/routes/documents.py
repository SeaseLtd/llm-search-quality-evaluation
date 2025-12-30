import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep, ValidatedCaseDep
from app.api.models.document import DocumentPublic, DocumentCreate
from app.models.case import Case
from app.models.document import Document
from app.api.models.message import Message

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=list[DocumentPublic])
def read_documents(
    session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Retrieve documents.
    """
    statement = (
        select(Document)
        .join(Document.case)
        .where(Case.owner_id == current_user.user_id)
    )
    return session.exec(statement).all()


@router.get("/{case_id}/{document_id}", response_model=DocumentPublic)
def read_document(
    session: SessionDep,
    validated_case: ValidatedCaseDep,
    document_id: str
) -> Any:
    """
    Get document by composite key (case_id, document_id).
    """
    document = session.get(Document, (document_id, validated_case.case_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("/{case_id}/", response_model=DocumentPublic)
def create_document(
    *,
    session: SessionDep,
    validated_case: ValidatedCaseDep,
    document_in: DocumentCreate
) -> Any:
    """
    Create new document.
    """
    document = Document.model_validate(document_in, update={"case_id": validated_case.case_id})
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


@router.put("/{case_id}/{document_id}", response_model=DocumentPublic)
def update_document(
    *,
    session: SessionDep,
    validated_case: ValidatedCaseDep,
    document_id: str,
    document_in: DocumentCreate,
) -> Any:
    """
    Update a document.
    """
    document = session.get(Document, (document_id, validated_case.case_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    update_dict = document_in.model_dump(exclude_unset=True)
    document.sqlmodel_update(update_dict)
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


@router.delete("/{case_id}/{document_id}")
def delete_document(
    session: SessionDep,
    validated_case: ValidatedCaseDep,
    document_id: str
) -> Message:
    """
    Delete a document.
    """
    document = session.get(Document, (document_id, validated_case.case_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    session.delete(document)
    session.commit()
    return Message(message="Document deleted successfully")

