import uuid
from typing import Any
import gzip
import json

import app
from fastapi import APIRouter, HTTPException, UploadFile, File
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep, ValidatedCaseDep
from app.api.models.case import CasePublic, CaseCreate, CaseUpdate, CaseDetailed, CaseUploadDataset

from app.models.case import Case
from app.models.query import Query
from app.models.rating import Rating
from app.models.document import Document
from app.api.models.message import Message

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("/", response_model=list[CasePublic])
def read_cases(
    session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Retrieve cases.
    """
    statement = (
        select(Case)
        .options(selectinload(Case.queries))
    )

    # Filter by owner_id only if not superuser
    if not current_user.is_superuser:
        statement = statement.where(Case.owner_id == current_user.user_id)

    cases = session.exec(statement).all()

    return [
        CasePublic.model_validate(
            case,
            update={
                "num_queries": len(case.queries),
                "updated_at": max([case.updated_at] + [query.updated_at for query in case.queries]) if case.queries else case.updated_at
            }
        )
        for case in cases
    ]


@router.get("/{case_id}", response_model=CaseDetailed)
def read_case(session: SessionDep, current_user: CurrentUser, case_id: uuid.UUID) -> CaseDetailed:
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
        .where(Case.case_id == case_id)
    )
    case: Case = session.exec(statement).one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not current_user.is_superuser and (case.owner_id != current_user.user_id):
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
    case = Case.model_validate(case_in, update={"owner_id": current_user.user_id})
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


@router.put("/{case_id}", response_model=CasePublic)
def update_case(
    *,
    session: SessionDep,
    validated_case: ValidatedCaseDep,
    case_in: CaseUpdate,
) -> Any:
    """
    Update an case.
    """

    update_dict = case_in.model_dump(exclude_unset=True)
    validated_case.sqlmodel_update(update_dict)
    session.add(validated_case)
    session.commit()
    session.refresh(validated_case)
    return validated_case


@router.delete("/{case_id}")
def delete_case(
    session: SessionDep, validated_case: ValidatedCaseDep
) -> Message:
    """
    Delete a case.
    """

    session.delete(validated_case)
    session.commit()
    return Message(message="Cases deleted successfully")


@router.post("/{case_id}/upload_dataset", response_model=CaseDetailed)
async def upload_dataset(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    case: ValidatedCaseDep,
    file: UploadFile = File(...)
) -> CaseDetailed:
    """
    Upload a dataset file (JSON or GZ) to a case.
    This operation will replace all existing queries, documents, and ratings.
    """

    try:
        # Validate file extension
        filename = file.filename or ""
        if not (filename.endswith('.json') or filename.endswith('.gz')):
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Only .json and .gz files are supported"
            )

        # Read file content
        content = await file.read()

        # Decompress if gzip
        if filename.endswith('.gz'):
            content = gzip.decompress(content)

        # Parse JSON
        dataset_data = json.loads(content.decode('utf-8'))

        # Validate dataset structure
        if not all(key in dataset_data for key in ['queries', 'documents', 'ratings', 'max_rating_value']):
            raise HTTPException(
                status_code=400,
                detail="Invalid dataset format. Required keys: queries, documents, ratings, max_rating_value"
            )

        # Delete all existing queries (cascade will delete ratings)
        # First get all queries for this case
        existing_queries = session.exec(
            select(Query).where(Query.case_id == case.case_id)
        ).all()

        for query in existing_queries:
            session.delete(query)

        # Delete all orphaned documents (documents not referenced by other cases)
        # For now, we delete all documents referenced by ratings of this case's queries
        # This is a simplified approach - in production you might want to track document usage
        existing_ratings = session.exec(
            select(Rating).where(Rating.query_id.in_([q.query_id for q in existing_queries]))
        ).all()

        doc_ids_to_check = {r.document_id for r in existing_ratings}
        for doc_id in doc_ids_to_check:
            # Check if document is still referenced by other ratings
            other_ratings = session.exec(
                select(Rating).where(
                    Rating.document_id == doc_id,
                    Rating.query_id.notin_([q.query_id for q in existing_queries])
                )
            ).first()

            if not other_ratings:
                doc = session.get(Document, doc_id)
                if doc:
                    session.delete(doc)

        case.max_rating_value = int(dataset_data['max_rating_value'])
        case.queries = [
            Query(
                case_id=case.case_id,
                query_id=query['id'],
                query=query['text'],
                ratings=[
                    Rating(
                        case_id=case.case_id,
                        query_id=query['id'],
                        document_id=rating['doc_id'],
                        position=position,
                        llm_rating=rating['score'],
                        explanation=rating['explanation'] if 'explanation' in rating else None,
                        document=Document(
                            case_id=case.case_id,
                            document_id=rating['doc_id'],
                            fields={
                                fieldName: value[0] if isinstance(value, list) and len(value) == 1 else value
                                for document in dataset_data['documents']
                                for fieldName, value in document['fields'].items()
                                if document['id'] == rating['doc_id']
                            }
                        )
                    )
                    for position, rating in enumerate(dataset_data['ratings']) if rating['query_id'] == query['id']
                ]
            ) for query in dataset_data['queries']
        ]

        session.commit()

        # Return the updated case using read_case logic
        return read_case(session=session, current_user=current_user, case_id=case.case_id)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except json.JSONDecodeError as e:
        app.logger.error(f"JSON decode error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    except gzip.BadGzipFile as e:
        app.logger.error(f"Gzip error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid gzip file")
    except Exception as e:
        app.logger.error(f"Unexpected error in upload_dataset: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

