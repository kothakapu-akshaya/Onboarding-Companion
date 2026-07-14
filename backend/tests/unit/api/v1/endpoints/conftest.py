from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest


class DummyModel(SimpleNamespace):
    def model_dump(self, *args, **kwargs):
        return dict(self.__dict__)


def result_rows(*rows):
    return SimpleNamespace(
        all=lambda: list(rows),
        first=lambda: rows[0] if rows else None,
        one=lambda: rows[0] if rows else None,
    )


@pytest.fixture
def mock_session():
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    session.rollback = Mock()
    session.delete = Mock()
    session.get = Mock()
    session.exec = Mock()
    return session


@pytest.fixture
def endpoint_user():
    user = DummyModel()
    user.id = uuid4()
    user.username = "test_user"
    user.name = "Test User"
    user.email = "test@example.com"
    user.is_active = True
    return user
