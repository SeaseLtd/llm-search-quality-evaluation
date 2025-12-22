from sqlmodel import Session

from app import crud
from tests.utils.user import create_random_user
from tests.utils.utils import random_lower_string

from app.models.case import Case, CaseCreate


def create_random_case(db: Session) -> Case:
    user = create_random_user(db)
    owner_id = user.id
    assert owner_id is not None
    title = random_lower_string()
    description = random_lower_string()
    case_in = CaseCreate(title=title, description=description)
    return crud.create_case(session=db, case_in=case_in, owner_id=owner_id)
