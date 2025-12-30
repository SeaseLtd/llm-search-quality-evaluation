import uuid
from typing import Any
import gzip
import json

import app
from fastapi import APIRouter, HTTPException, UploadFile, File
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep
from app.api.models.case import CasePublic, CaseCreate, CaseUpdate, CaseDetailed, CaseUploadDataset

from app.models.case import Case
from app.models.query import Query
from app.models.rating import Rating
from app.models.document import Document
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
        select(Case)
        .options(selectinload(Case.queries))
        .offset(skip)
        .limit(limit)
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
    if not current_user.is_superuser and (case.owner_id != current_user.user_id):
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
    if not current_user.is_superuser and (case.owner_id != current_user.user_id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    session.delete(case)
    session.commit()
    return Message(message="Cases deleted successfully")


@router.post("/{id}/upload_dataset", response_model=CaseDetailed)
async def upload_dataset(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    file: UploadFile = File(...)
) -> CaseDetailed:
    """
    Upload a dataset file (JSON or GZ) to a case.
    This operation will replace all existing queries, documents, and ratings.
    """
    # Get the case
    case = session.get(Case, id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not current_user.is_superuser and (case.owner_id != current_user.user_id):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Validate file extension
    filename = file.filename or ""
    if not (filename.endswith('.json') or filename.endswith('.gz')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .json and .gz files are supported"
        )

    try:
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

        dataset = CaseUploadDataset(**dataset_data)

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    except gzip.BadGzipFile:
        raise HTTPException(status_code=400, detail="Invalid gzip file")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

    # Delete all existing queries (cascade will delete ratings)
    # First get all queries for this case
    existing_queries = session.exec(
        select(Query).where(Query.case_id == id)
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

    session.commit()

    # Update case max_rating_value
    case.max_rating_value = dataset.max_rating_value
    session.add(case)
    session.commit()

    # Create documents first and track their mapping
    document_id_mapping = {}  # old_id -> new_uuid
    for doc_data in dataset.documents:
        old_id = doc_data.get('id')
        if not old_id:
            continue

        # Create new document
        new_doc = Document(
            fields=doc_data.get('fields', {})
        )
        session.add(new_doc)
        session.flush()  # Get the new UUID
        document_id_mapping[old_id] = new_doc.document_id

    # Create queries and track their mapping
    query_id_mapping = {}  # old_id -> new_uuid
    for query_data in dataset.queries:
        old_id = query_data.get('id')
        query_text = query_data.get('text', '')

        if not old_id or not query_text:
            continue

        # Create new query
        new_query = Query(
            query=query_text,
            case_id=id
        )
        session.add(new_query)
        session.flush()  # Get the new UUID
        query_id_mapping[old_id] = new_query.query_id

    # Create ratings
    for rating_data in dataset.ratings:
        old_query_id = rating_data.get('query_id')
        old_doc_id = rating_data.get('doc_id')

        # Map old IDs to new UUIDs
        new_query_id = query_id_mapping.get(old_query_id)
        new_doc_id = document_id_mapping.get(old_doc_id)

        if not new_query_id or not new_doc_id:
            continue

        # Create new rating
        new_rating = Rating(
            query_id=new_query_id,
            document_id=new_doc_id,
            llm_rating=rating_data.get('score'),
            user_rating=None,
            explanation=rating_data.get('explanation'),
            position=rating_data.get('position', 0)
        )
        session.add(new_rating)

    session.commit()

    # Return the updated case using read_case logic
    return read_case(session=session, current_user=current_user, id=id)

