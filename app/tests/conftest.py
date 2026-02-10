# conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from api import create_application
from database.database import get_session
from models.ml_model import MLModel  


TEST_FEATURES = [
    "Height (cm)",
    "Weight (kg)",
    "BMI",
    "Cholesterol Level (mg/dL)",
    "Blood Glucose Level (mg/dL)",
    "Stress Levels",
    "Vision Sharpness",
    "Hearing Ability (dB)",
    "Bone Density (g/cm²)",
    "BP_Systolic",
    "BP_Diastolic",
]


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        if session.get(MLModel, 1) is None:
            session.add(
                MLModel(
                    id=1,
                    name="Test Model",
                    price_per_task=25,
                    feature_names=TEST_FEATURES,
                )
            )
            session.commit()

        yield session


@pytest.fixture
def client(session: Session):
    app = create_application()

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
