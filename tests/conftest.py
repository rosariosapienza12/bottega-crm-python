import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base


@pytest.fixture
def db():
    """Database SQLite in memoria, vuoto per ogni test."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()
