import uuid
from typing import Any

import app
from fastapi import APIRouter, HTTPException
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep
from app.api.models.case import CasePublic, CaseCreate, CaseUpdate, CaseDetailed

from app.models.case import Case
from app.models.query import Query
from app.models.rating import Rating
from app.api.models.message import Message

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("/", response_model=list[CasePublic])
def read_cases(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve cases.
    """
    statement = (
        select(Case).
        offset(skip).
        limit(limit)
    )

    # Filter by owner_id only if not superuser
    if not current_user.is_superuser:
        statement = statement.where(Case.owner_id == current_user.user_id)

    cases = session.exec(statement).all()

    # Return empty list if no cases found (not 404)
    return cases


@router.get("/{id}", response_model=CaseDetailed)
def read_case(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> CaseDetailed:
    """
    Get case by ID with all queries, documents and ratings.
    """
    # Get the case with all its queries
    statement = (
        select(Case)
        .options(
            selectinload(Case.queries)
            .selectinload(Query.ratings)
            .selectinload(Rating.document)
        )
        .where(Case.case_id == id)
    )
    case: Case = session.exec(statement).one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not current_user.is_superuser and (case.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # for query in case.queries:
    #     app.logger.info(f"Query ID: {query.query_id}, Ratings count: {len(query.ratings)}")
    #     for rating in sorted(query.ratings, key=lambda r: r.position):
    #         app.logger.info(f"Rating {rating.position} - Query ID: {rating.query_id}, Document ID: {rating.document_id}, LLM Rating: {rating.llm_rating}, Document: {rating.document.fields['title']}")

    return CaseDetailed(case)


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
