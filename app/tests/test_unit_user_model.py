import pytest
from sqlmodel import Session

from models.user import User


def test_create_user(session: Session):
    user = User(id=1, email="test@mail.ru", password="password123")
    session.add(user)
    session.commit()

    db_user = session.get(User, 1)
    assert db_user is not None
    assert db_user.email == "test@mail.ru"


def test_fail_duplicate_email(session: Session):
    u1 = User(id=1, email="dup@mail.ru", password="password123")
    u2 = User(id=2, email="dup@mail.ru", password="password456")

    session.add(u1)
    session.commit()

    session.add(u2)
    with pytest.raises(Exception):
        session.commit()


def test_delete_user(session: Session):
    session.add(User(id=1, email="del@mail.ru", password="password123"))
    session.commit()

    u = session.get(User, 1)
    assert u is not None

    session.delete(u)
    session.commit()

    assert session.get(User, 1) is None
