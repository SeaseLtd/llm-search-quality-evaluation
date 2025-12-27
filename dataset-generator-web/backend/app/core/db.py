import random

from sqlmodel import Session, create_engine, select, SQLModel

import app
from app import crud
from app.api.models.case import CaseCreate
from app.core.config import settings

# Import all models to register them with SQLModel metadata before create_all()
from app.models import (
    User, UserCreate,
    Case,
    Query,
    Document,
    Rating
)


engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def init_db(session: Session) -> None:
    app.logger.info("Creating all tables...")
    SQLModel.metadata.create_all(engine)
    app.logger.info("Tables created successfully")

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            full_name="Admin",
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
            upload_limit_mb=1000,
        )
        user = crud.create_user(session=session, user_create=user_in)
        app.logger.info(f"Created user: {user.email}")

    # Create a default case if it doesn't exist
    case = session.exec(
        select(Case).where(Case.owner_id == user.user_id)
    ).first()
    if not case:
        case_in = CaseCreate(
            title="Default Case",
            description="Default case for initial data",
            max_rating_value=5,
            document_title_field_name="title"
        )
        case = crud.create_case(session=session, case_in=case_in, owner_id=user.user_id)
        app.logger.info(f"Created case: {case.title}")

    # Create 5 queries if they don't exist
    existing_queries = session.exec(
        select(Query).where(Query.case_id == case.case_id)
    ).all()

    if len(existing_queries) < 5:
        queries_to_create = 5 - len(existing_queries)
        for i in range(len(existing_queries) + 1, len(existing_queries) + queries_to_create + 1):
            query = Query(
                query=f"Sample query {i}",
                case_id=case.case_id
            )
            session.add(query)
            app.logger.info(f"Created query: {query.query}")
        session.commit()

    # Get all queries for the case
    queries = session.exec(
        select(Query).where(Query.case_id == case.case_id)
    ).all()

    # Create 10 documents if they don't exist
    existing_documents_count = session.exec(select(Document)).all()
    if len(existing_documents_count) < 10:
        documents_to_create = 10 - len(existing_documents_count)
        for i in range(len(existing_documents_count) + 1, len(existing_documents_count) + documents_to_create + 1):
            document = Document(
                fields={
                    "title": f"Document {i}",
                    "content": f"This is the content of document {i}",
                    "category": f"Category {(i % 3) + 1}"
                }
            )
            session.add(document)
            app.logger.info(f"Created document: Document {i}")
        session.commit()

    # Get all documents
    documents = session.exec(select(Document)).all()

    # Create ratings for each query-document pair if they don't exist
    for query in queries:
        current_position = 0
        for document in documents:
            existing_rating = session.exec(
                select(Rating).where(
                    Rating.query_id == query.query_id,
                    Rating.document_id == document.document_id
                )
            ).first()

            if not existing_rating:
                rating = Rating(
                    query_id=query.query_id,
                    document_id=document.document_id,
                    position=(current_position := current_position + 1),
                    user_rating=random.randint(0, case.max_rating_value) if random.randint(0,1) == 0 else None,
                    llm_rating=(hash(str(query.query_id) + str(document.document_id)) % 5) + 1,  # Random rating 1-5
                    explanation=f"Auto-generated rating from query {query.query_id} and document {document.document_id}" if random.randint(0,1) == 0 else None
                )
                session.add(rating)

    session.commit()
    app.logger.info(f"Created ratings for {len(queries)} queries and {len(documents)} documents")
