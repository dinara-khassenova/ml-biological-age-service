from typing import Dict
from fastapi import APIRouter

router = APIRouter()

@router.get(
    "/",
    response_model=Dict[str, str],
    summary="Root endpoint",
    description="Returns a welcome message",
)
def index() -> Dict[str, str]:
    """
    Root endpoint returning welcome message.
    Используется как smoke-test, что API поднялось.
    """
    return {"message": "Welcome to ML Biological Age Service API"}


@router.get(
    "/health",
    response_model=Dict[str, str],
    summary="Health check endpoint",
    description="Returns service health status",
)
def health_check() -> Dict[str, str]:
    """
    Health check endpoint for Docker / monitoring.
    """
    return {"status": "healthy"}
