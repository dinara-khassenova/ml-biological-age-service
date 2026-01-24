from __future__ import annotations
from typing import List, Optional
from sqlmodel import Session, select
from models.ml_model import MLModel


def get_model_by_id(model_id: int, session: Session) -> Optional[MLModel]:
    """
    Get ML model meta by ID.
    """
    try:
        statement = select(MLModel).where(MLModel.id == model_id)
        model = session.exec(statement).first()
        return model
    except Exception:
        raise


def get_all_models(session: Session) -> List[MLModel]:
    """
    List all ML models.
    """
    try:
        statement = select(MLModel)
        models = session.exec(statement).all()
        return models
    except Exception:
        raise


def create_model(model: MLModel, session: Session) -> MLModel:
    """
    Create new ML model meta.
    """
    try:
        session.add(model)
        session.commit()
        session.refresh(model)
        return model
    except Exception:
        session.rollback()
        raise
