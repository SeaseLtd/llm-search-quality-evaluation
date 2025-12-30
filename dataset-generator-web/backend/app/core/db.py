import random
import uuid

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
            first_name="Admin",
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
            upload_limit_mb=1000,
        )
        user = crud.create_user(session=session, user_create=user_in)
        app.logger.info(f"Created user: {user.email}")
        session.commit()

    # Create a default case if it doesn't exist
    case = session.exec(
        select(Case).where(Case.owner_id == user.user_id)
    ).first()
    if not case:
        case_id = uuid.uuid4()
        case = Case(
            case_id=case_id,
            title="Sample Case",
            description="Default case for initial data",
            max_rating_value=5,
            document_title_field_name="title",
            owner_id=user.user_id,
            queries=[
                Query(
                    case_id=case_id,
                    query_id=f"query_{query_index}",
                    query=f"Sample query {query_index}",
                    ratings=[
                        Rating(
                            position=idx,
                            llm_rating=random.randint(1, 5),
                            document=Document(
                                case_id=case_id,
                                query_id=f"query_{query_index}",
                                document_id=f"q_{query_index}_doc_{idx}",
                                fields={
                                    "title": f"Document {idx}",
                                    "content": f"This is the content of document {idx}",
                                    "category": f"Category {(idx % 3) + 1}"
                                }
                            )
                        )
                        for idx in range(1, 10)
                    ]
                )
                for query_index in range(1, 10)
            ]
        )
        session.add(case)
        session.commit()
        app.logger.info(f"Created case: {case.title}")

    session.commit()