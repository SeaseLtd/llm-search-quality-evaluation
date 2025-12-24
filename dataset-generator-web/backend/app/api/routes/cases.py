import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep

from app.models.case import Case, CasePublic, CaseUpdate, CaseCreate, CaseDetailed
from app.models.query import Query, QueryPublic
from app.models.rating import Rating
from app.models.document import Document, DocumentWithRating
from app.models.message import Message

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("/", response_model=list[CasePublic])
def read_cases(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve cases.
    """

    statement = (
        select(Case)
        .where(Case.owner_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    if not current_user.is_superuser:
        statement = statement.where(Case.owner_id == current_user.id)
    cases = session.exec(statement).all()

    return cases


@router.get("/{id}", response_model=CaseDetailed)
def read_case(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get case by ID with all queries, documents and ratings.
    """
    # Get all queries for this case
    queries_statement = (select(Case)
                         .join(Query)
                         .join(Rating)
                         .join(Document)
                         .where(Query.case_id == id))
    case: Case = session.exec(queries_statement).one()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not current_user.is_superuser and (case.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    return CaseDetailed(
        id=case.id,
        title=case.title,
        description=case.description,
        owner_id=case.owner_id,
        queries=case.queries
    )


@router.post("/", response_model=CasePublic)
def create_case(
    *, session: SessionDep, current_user: CurrentUser, case_in: CaseCreate
) -> Any:
    """
    Create new case.
    """
    case = Case.model_validate(case_in, update={"owner_id": current_user.id})
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


@router.put("/{id}", response_model=CasePublic)
def update_case(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    case_in: CaseUpdate,
) -> Any:
    """
    Update an case.
    """
    case = session.get(Case, id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not current_user.is_superuser and (case.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    update_dict = case_in.model_dump(exclude_unset=True)
    case.sqlmodel_update(update_dict)
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


@router.delete("/{id}")
def delete_case(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a case.
    """
    case = session.get(Case, id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not current_user.is_superuser and (case.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    session.delete(case)
    session.commit()
    return Message(message="Cases deleted successfully")
