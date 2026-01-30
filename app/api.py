from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn

from database.database import init_db
from database.config import get_settings

from routes.home import router as home_router
from routes.auth import router as auth_router
from routes.wallet import router as wallet_router
from routes.task import router as tasks_router


logger = logging.getLogger(__name__)
settings = get_settings()

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.API_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(home_router, tags=['Home'])
    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    app.include_router(wallet_router, prefix="/api/wallet", tags=["Wallet"])
    app.include_router(tasks_router, prefix="/api/tasks", tags=["Tasks"])

    return app


app = create_application()

@app.on_event("startup") 
def on_startup():
    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Application shutting down...")


if __name__ == "__main__":
    """
    Локальный запуск без Docker:
    python api.py
    """
    logging.basicConfig(level=logging.DEBUG)
    uvicorn.run(
        "api:app",          
        host="0.0.0.0",     
        port=8080,          
        reload=True,        
        log_level="info",
    )
