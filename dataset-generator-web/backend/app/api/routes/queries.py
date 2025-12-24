import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models.query import Query, QueryPublic, QueryCreate
from app.models.case import Case
from app.models.message import Message

router = APIRouter(prefix="/queries", tags=["queries"])


@router.get("/", response_model=list[QueryPublic])
def read_queries(
    session: SessionDep,
    current_user: CurrentUser,
    case_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100
) -> list[QueryPublic]:
    """
    Retrieve queries. Optionally filter by case_id.
    """

    statement = (
        select(Query)
        .join(Case)
        .offset(skip)
        .limit(limit)
    )

    if case_id:
        # Verify the user has access to this case
        case = session.get(Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        if not current_user.is_superuser and (case.owner_id != current_user.id):
            raise HTTPException(status_code=400, detail="Not enough permissions")

        statement = statement.where(Query.case_id == case_id)
    if not current_user.is_superuser:
        statement = statement.where(Case.owner_id == current_user.id)
    queries = session.exec(statement).all()
    return queries


@router.get("/{id}", response_model=QueryPublic)
def read_query(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get query by ID.
    """
    query = session.get(Query, id)
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    # Check permissions via the case
    case = session.get(Case, query.case_id)
    if not current_user.is_superuser and (case.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    return query


@router.post("/", response_model=QueryPublic)
def create_query(
    *, session: SessionDep, current_user: CurrentUser, query_in: QueryCreate, case_id: uuid.UUID
) -> Any:
    """
    Create new query.
    """
    # Verify the user has access to this case
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not current_user.is_superuser and (case.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    query = Query.model_validate(query_in, update={"case_id": case_id})
    session.add(query)
    session.commit()
    session.refresh(query)
    return query


@router.put("/{id}", response_model=QueryPublic)
def update_query(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    query_in: QueryCreate,
) -> Any:
    """
    Update a query.
    """
    query = session.get(Query, id)
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    # Check permissions via the case
    case = session.get(Case, query.case_id)
    if not current_user.is_superuser and (case.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    update_dict = query_in.model_dump(exclude_unset=True)
    query.sqlmodel_update(update_dict)
    session.add(query)
    session.commit()
    session.refresh(query)
    return query


@router.delete("/{id}")
def delete_query(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a query.
    """
    query = session.get(Query, id)
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    # Check permissions via the case
    case = session.get(Case, query.case_id)
    if not current_user.is_superuser and (case.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    session.delete(query)
    session.commit()
    return Message(message="Query deleted successfully")

