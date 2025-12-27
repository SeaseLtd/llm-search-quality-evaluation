import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.api.models.rating import RatingDetailed, RatingCreate
from app.models.rating import Rating
from app.models.query import Query
from app.models.document import Document
from app.models.case import Case
from app.api.models.message import Message

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.get("/", response_model=list[RatingDetailed])
def read_ratings(
    session: SessionDep,
    current_user: CurrentUser,
    query_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100
) -> list[RatingDetailed]:
    """
    Retrieve ratings. Optionally filter by query_id or document_id.
    """
    statement = select(Rating)

    if query_id:
        query = session.get(Query, query_id)
        if not query:
            raise HTTPException(status_code=404, detail="Query not found")

        # Check permissions via the case
        case = session.get(Case, query.case_id)
        if not current_user.is_superuser and (case.owner_id != current_user.user_id):
            raise HTTPException(status_code=400, detail="Not enough permissions")

        statement = statement.where(Rating.query_id == query_id)

    if document_id:
        document = session.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        statement = statement.where(Rating.document_id == document_id)

    # If no filters and not superuser, show only ratings for user's cases
    if not query_id and not document_id and not current_user.is_superuser:
        statement = (
            statement
            .join(Query)
            .join(Case)
            .where(Case.owner_id == current_user.user_id)
        )
    ratings = session.exec(statement.offset(skip).limit(limit)).all()
    return ratings


@router.get("/{query_id}/{document_id}", response_model=RatingDetailed)
def read_rating(
    session: SessionDep,
    current_user: CurrentUser,
    query_id: uuid.UUID,
    document_id: uuid.UUID
) -> RatingDetailed:
    """
    Get rating by query_id and document_id.
    """
    rating = session.exec(
        select(Rating).where(
            Rating.query_id == query_id,
            Rating.document_id == document_id
        )
    ).first()

    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")

    # Check permissions via the query's case
    query = session.get(Query, query_id)
    if query:
        case = session.get(Case, query.case_id)
        if not current_user.is_superuser and (case.owner_id != current_user.user_id):
            raise HTTPException(status_code=400, detail="Not enough permissions")

    return rating


@router.post("/", response_model=RatingDetailed)
def create_rating(
    *, session: SessionDep, current_user: CurrentUser, rating_in: RatingCreate
) -> Any:
    """
    Create new rating.
    """
    # Verify query exists and user has permission
    query = session.get(Query, rating_in.query_id)
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    case = session.get(Case, query.case_id)
    if not current_user.is_superuser and (case.owner_id != current_user.user_id):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Verify document exists
    document = session.get(Document, rating_in.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if rating already exists
    existing_rating = session.exec(
        select(Rating).where(
            Rating.query_id == rating_in.query_id,
            Rating.document_id == rating_in.document_id
        )
    ).first()

    if existing_rating:
        raise HTTPException(status_code=400, detail="Rating already exists for this query-document pair")

    rating = Rating.model_validate(rating_in)
    session.add(rating)
    session.commit()
    session.refresh(rating)
    return rating


@router.put("/{query_id}/{document_id}", response_model=RatingDetailed)
def update_rating(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    query_id: uuid.UUID,
    document_id: uuid.UUID,
    rating_in: RatingCreate,
) -> Any:
    """
    Update a rating.
    """
    rating = session.exec(
        select(Rating).where(
            Rating.query_id == query_id,
            Rating.document_id == document_id
        )
    ).first()

    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")

    # Check permissions via the query's case
    query = session.get(Query, query_id)
    if query:
        case = session.get(Case, query.case_id)
        if not current_user.is_superuser and (case.owner_id != current_user.user_id):
            raise HTTPException(status_code=400, detail="Not enough permissions")

    update_dict = rating_in.model_dump(exclude_unset=True, exclude={"query_id", "document_id"})
    rating.sqlmodel_update(update_dict)
    session.add(rating)
    session.commit()
    session.refresh(rating)
    return rating


@router.delete("/{query_id}/{document_id}")
def delete_rating(
    session: SessionDep,
    current_user: CurrentUser,
    query_id: uuid.UUID,
    document_id: uuid.UUID
) -> Message:
    """
    Delete a rating.
    """
    rating = session.exec(
        select(Rating).where(
            Rating.query_id == query_id,
            Rating.document_id == document_id
        )
    ).first()

    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")

    # Check permissions via the query's case
    query = session.get(Query, query_id)
    if query:
        case = session.get(Case, query.case_id)
        if not current_user.is_superuser and (case.owner_id != current_user.user_id):
            raise HTTPException(status_code=400, detail="Not enough permissions")

    session.delete(rating)
    session.commit()
    return Message(message="Rating deleted successfully")

