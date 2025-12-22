from sqlmodel import Session, create_engine, select, SQLModel

from app import crud
from app.core.config import settings
from app.models.user import User
from app.models.case import Case
from app.models.query import Query
from app.models.document import Document
from app.models.rating import Rating

import app

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines

    # This works because the models are already imported and registered from app.models
    SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = User(
            full_name="Admin",
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)
        app.logger.info(f"Created user: {user.email}")

    # Create a default case if it doesn't exist
    case = session.exec(
        select(Case).where(Case.owner_id == user.id)
    ).first()
    if not case:
        case_in = Case(
            title="Default Case",
            description="Default case for initial data"
        )
        case = crud.create_case(session=session, case_in=case_in, owner_id=user.id)
        app.logger.info(f"Created case: {case.title}")

    # Create 5 queries if they don't exist
    existing_queries = session.exec(
        select(Query).where(Query.case_id == case.id)
    ).all()

    if len(existing_queries) < 5:
        queries_to_create = 5 - len(existing_queries)
        for i in range(len(existing_queries) + 1, len(existing_queries) + queries_to_create + 1):
            query = Query(
                query=f"Sample query {i}",
                case_id=case.id
            )
            session.add(query)
            app.logger.info(f"Created query: {query.query}")
        session.commit()

    # Get all queries for the case
    queries = session.exec(
        select(Query).where(Query.case_id == case.id)
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
        for document in documents:
            existing_rating = session.exec(
                select(Rating).where(
                    Rating.query_id == query.id,
                    Rating.document_id == document.id
                )
            ).first()

            if not existing_rating:
                rating = Rating(
                    query_id=query.id,
                    document_id=document.id,
                    llm_rating=(hash(str(query.id) + str(document.id)) % 5) + 1  # Random rating 1-5
                )
                session.add(rating)

    session.commit()
    app.logger.info(f"Created ratings for {len(queries)} queries and {len(documents)} documents")

