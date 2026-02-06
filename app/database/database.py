from __future__ import annotations

from sqlmodel import SQLModel, Session, create_engine, select

from database.config import get_settings
import models
from models import MLModel
from ml.utils import load_features_from_meta

def get_database_engine():
    settings = get_settings()

    return create_engine(
        url=settings.DATABASE_URL_psycopg,
        echo=settings.DEBUG,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

engine = get_database_engine()


def get_session():
    with Session(engine) as session:
        yield session


def init_db(drop_all: bool = False) -> None:
    if drop_all:
        SQLModel.metadata.drop_all(engine)

    SQLModel.metadata.create_all(engine)

    # Base data
    with Session(engine) as session:
        features = load_features_from_meta()

        # ML model #1
        m1 = session.exec(select(MLModel).where(MLModel.id == 1)).first()
        if m1 is None:
            session.add(
                MLModel(
                    id=1,
                    name="BioAge v2 (Ridge)",
                    price_per_task=25,
                    feature_names=features,
                )
            )
        else:
            m1.name = "BioAge v2 (Ridge)"
            m1.price_per_task = 25
            m1.feature_names = features

        # ML model #2
        m2 = session.exec(select(MLModel).where(MLModel.id == 2)).first()
        if m2 is None:
            session.add(
                MLModel(
                    id=2,
                    name="BioAge v2 (Ridge Lite)",
                    price_per_task=10,
                    feature_names=features,
                )
            )
        else:
            m2.name = "BioAge v2 (Ridge Lite)"
            m2.price_per_task = 10
            m2.feature_names = features

        session.commit()


