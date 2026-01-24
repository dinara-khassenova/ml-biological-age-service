from __future__ import annotations

from sqlmodel import Session

from database.database import engine, init_db
from services.auth import RegAuthService
from services.billing import BillingService
from services.task import TaskService
from services.admin import AdminService
from services.crud import transaction as tx_crud
from models.assessment import AssessmentTask

USER1_EMAIL = "user1@test.com"
USER2_EMAIL = "user2@test.com"
ADMIN_EMAIL = "admin@test.com"
DEFAULT_PASSWORD = "password1"


def register_demo_users(auth: RegAuthService):
    user1 = auth.register(email=USER1_EMAIL, password=DEFAULT_PASSWORD, role="USER")
    user2 = auth.register(email=USER2_EMAIL, password=DEFAULT_PASSWORD, role="USER")
    admin = auth.register(email=ADMIN_EMAIL, password=DEFAULT_PASSWORD, role="ADMIN")
    return user1, user2, admin


def demo_scenario() -> None:
    with Session(engine) as session:
        auth = RegAuthService(session)
        billing = BillingService(session)
        task_service = TaskService(session, billing)
        admin_service = AdminService(session, billing)

        print("\n=== DEMO SCENARIO START ===")

        # 1) Create demo users
        user1, user2, admin = register_demo_users(auth)
        print(f"[AUTH] USER1: id={user1.id}, email={user1.email}, role={user1.role}")
        print(f"[AUTH] USER2: id={user2.id}, email={user2.email}, role={user2.role}")
        print(f"[AUTH] ADMIN: id={admin.id}, email={admin.email}, role={admin.role}")

        # 2) Topup users
        billing.topup(user1.id, amount=100)
        billing.topup(user2.id, amount=50)
        print("[BILLING] USER1 credited: +100")
        print("[BILLING] USER2 credited: +50")

        # 3) Balances before
        print(f"[BALANCE] USER1 before: {billing.balance(user1.id)} credits")
        print(f"[BALANCE] USER2 before: {billing.balance(user2.id)} credits")

        # 4) Run tasks 
        t1 = task_service.run_task(
            AssessmentTask(
                user_id=user1.id,
                answers={"age": 40, "bmi": 26, "glucose": 5.1},
            )
        )
        print(f"[TASK] USER1 status: {t1.status}")
        if t1.status == "DONE":
            print("[TASK] USER1 biological age:", t1.result.get("biological_age"))
        else:
            print("[TASK] USER1 error:", t1.error_message)

        t2 = task_service.run_task(
            AssessmentTask(
                user_id=user2.id,
                answers={"age": 32, "bmi": 24, "glucose": 4.8},
            )
        )
        print(f"[TASK] USER2 status: {t2.status}")
        if t2.status == "DONE":
            print("[TASK] USER2 biological age:", t2.result.get("biological_age"))
        else:
            print("[TASK] USER2 error:", t2.error_message)

        # 5) Balances after
        print(f"[BALANCE] USER1 after: {billing.balance(user1.id)} credits")
        print(f"[BALANCE] USER2 after: {billing.balance(user2.id)} credits")

        # 6) User transactions
        print("\n[TRANSACTIONS] USER1")
        for tx in tx_crud.get_user_transactions(user1.id, session):
            print(tx)

        print("\n[TRANSACTIONS] USER2")
        for tx in tx_crud.get_user_transactions(user2.id, session):
            print(tx)

        # 7) Admin: all transactions
        print("\n[TRANSACTIONS] ALL (ADMIN VIEW)")
        for tx in admin_service.all_transactions(admin.id):
            print(tx)

        print("\n=== DEMO SCENARIO END ===\n")


def main() -> None:
    print("Initializing database...")
    init_db(drop_all=True)  # по лекции чистим БД перед каждой инициализацией
    demo_scenario()


if __name__ == "__main__":
    main()


'''
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
'''