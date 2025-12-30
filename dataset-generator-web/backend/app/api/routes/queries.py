import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select
from sqlalchemy.orm import selectinload

import app
from app.api.deps import CurrentUser, SessionDep, ValidatedCaseDep
from app.api.models.query import QueryPublic, QueryCreate
from app.models import Rating
from app.models.query import Query
from app.models.case import Case
from app.api.models.message import Message

router = APIRouter(prefix="/queries", tags=["queries"])


@router.get("/", response_model=list[QueryPublic])
def read_queries(
    session: SessionDep,
    current_user: CurrentUser,
    case_id: uuid.UUID | None = None,
    add_documents: bool = False
) -> list[QueryPublic]:
    """
    Retrieve queries. Optionally filter by case_id.
    """

    statement = (
        select(Query)
        .join(Case)
    )

    if case_id:
        # Verify the user has access to this case
        case = session.get(Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        if not current_user.is_superuser and (case.owner_id != current_user.user_id):
            raise HTTPException(status_code=400, detail="Not enough permissions")

        statement = statement.where(Query.case_id == case_id)
    if not current_user.is_superuser:
        statement = statement.where(Case.owner_id == current_user.user_id)

    if add_documents:
        statement.options(
            selectinload(Query.ratings)
            .selectinload(Rating.document)
        )

    queries: list[Query] = session.exec(statement).all()

    for query in queries:
        app.logger.info(f"Query ID: {query.query_id}, Ratings count: {len(query.ratings)}")
        if add_documents:
            for rating in query.ratings:
                app.logger.info(f" - {rating.llm_rating} {rating.document}")

    return [
        QueryPublic(query)
        for query in queries
    ]


@router.get("/{case_id}/{query_id}", response_model=QueryPublic)
def read_query(
    session: SessionDep,
    validated_case: ValidatedCaseDep,
    query_id: str
) -> Any:
    """
    Get query by composite key (query_id, case_id).
    """
    query = session.get(Query, (query_id, validated_case.case_id))
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    return query


@router.post("/{case_id}/", response_model=QueryPublic)
def create_query(
    *, session: SessionDep, validated_case: ValidatedCaseDep, query_in: QueryCreate
) -> Any:
    """
    Create new query.
    """
    query = Query.model_validate(query_in, update={"case_id": validated_case.case_id})
    session.add(query)
    session.commit()
    session.refresh(query)
    return query


@router.put("/{case_id}/{query_id}", response_model=QueryPublic)
def update_query(
    *,
    session: SessionDep,
    validated_case: ValidatedCaseDep,
    query_id: str,
    query_in: QueryCreate,
) -> Any:
    """
    Update a query.
    """
    query = session.get(Query, (query_id, validated_case.case_id))
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")


    update_dict = query_in.model_dump(exclude_unset=True)
    query.sqlmodel_update(update_dict)
    session.add(query)
    session.commit()
    session.refresh(query)
    return query


@router.delete("/{case_id}/{query_id}")
def delete_query(
    session: SessionDep,
    validated_case: ValidatedCaseDep,
    query_id: str
) -> Message:
    """
    Delete a query.
    """
    query = session.get(Query, (query_id, validated_case.case_id))
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    session.delete(query)
    session.commit()
    return Message(message="Query deleted successfully")

