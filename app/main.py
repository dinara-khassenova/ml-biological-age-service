from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict
import uvicorn
import logging

from models.user import User

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ML Service API",
    description="API для ML сервиса (учебный проект)",
    version="1.0.0",
)

@app.get("/", response_model=Dict[str, str])
async def index() -> Dict[str, str]:
    try:
        user = User(id=1, email="user@test.com", password="password1")
        logger.info(f"index ok: {user}")
        return {"message": f"Hello world! User: {user}"}
    except Exception as e:
        logger.error(f"index error: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.get("/health")
async def health_check() -> Dict[str, str]:
    logger.info("health ok")
    return {"status": "healthy"}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    logger.warning(f"HTTPException: {exc.detail} url={request.url}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="debug",
    )
