from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database.database import get_session
from database.config import get_settings

from services.crud import ml_model as ml_model_crud
from schemas.ml_model import MLModelOut
from models.ml_model import MLModel


router = APIRouter()

@router.get("", response_model=list[MLModelOut])
def list_models(session: Session = Depends(get_session)) -> list[MLModelOut]:
    models = ml_model_crud.get_all_models(session)
    return [MLModelOut.model_validate(m) for m in models]


@router.get("/default", response_model=MLModelOut)
def get_default_model(session: Session = Depends(get_session)):
    settings = get_settings()

    model = session.exec(
        select(MLModel).where(MLModel.id == settings.DEFAULT_MODEL_ID)
    ).first()

    if not model:
        raise HTTPException(
            status_code=404,
            detail="Default model not found"
        )

    return MLModelOut.model_validate(model)


