import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep, ValidatedCaseDep
from app.api.models.rating import RatingDetailed, RatingCreate, UserRatingUpdate
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
    query_id: str | None = None,
    document_id: str | None = None
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
    ratings = session.exec(statement).all()
    return ratings


@router.get("/{case_id}/{query_id}/{document_id}", response_model=RatingDetailed)
def read_rating(
    session: SessionDep,
    validated_case: ValidatedCaseDep,
    query_id: str,
    document_id: str
) -> RatingDetailed:
    """
    Get rating by composite key (case_id, query_id, document_id).
    """
    rating = session.get(Rating, (validated_case.case_id, query_id, document_id))
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")


    return rating


@router.post("/{case_id}/", response_model=RatingDetailed)
def create_rating(
    *, session: SessionDep, validated_case: ValidatedCaseDep, rating_in: RatingCreate
) -> Any:
    """
    Create new rating.
    """
    # Verify query exists
    query = session.get(Query, (rating_in.query_id, validated_case.case_id))
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    # Verify document exists
    document = session.get(Document, (rating_in.document_id, validated_case.case_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if rating already exists
    existing_rating = session.get(Rating, (validated_case.case_id, rating_in.query_id, rating_in.document_id))
    if existing_rating:
        raise HTTPException(status_code=400, detail="Rating already exists for this query-document pair")

    rating = Rating.model_validate(rating_in, update={"case_id": validated_case.case_id})
    session.add(rating)
    session.commit()
    session.refresh(rating)
    return rating


@router.put("/{case_id}/{query_id}/{document_id}", response_model=RatingDetailed)
def update_user_rating(
    *,
    session: SessionDep,
    validated_case: ValidatedCaseDep,
    query_id: str,
    document_id: str,
    rating_in: UserRatingUpdate,
) -> Any:
    """
    Update a rating.
    """
    rating = session.get(Rating, (validated_case.case_id, query_id, document_id))
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")

    update_dict = rating_in.model_dump(exclude_unset=True, exclude={"case_id", "query_id", "document_id"})
    rating.sqlmodel_update(update_dict)
    session.add(rating)
    session.commit()
    session.refresh(rating)
    return rating


@router.delete("/{case_id}/{query_id}/{document_id}")
def delete_rating(
    session: SessionDep,
    validated_case: ValidatedCaseDep,
    query_id: str,
    document_id: str
) -> Message:
    """
    Delete a rating.
    """
    rating = session.get(Rating, (validated_case.case_id, query_id, document_id))
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")


    session.delete(rating)
    session.commit()
    return Message(message="Rating deleted successfully")

