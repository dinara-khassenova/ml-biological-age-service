from sqlmodel import Session

from tests.helpers import register_user, login_user, auth_headers

from services.billing import BillingService
from services.crud import task as task_crud
from services.crud import ml_model as ml_model_crud
from models.enum import TaskStatus, TransactionType
from ml.runtime_model import RuntimeMLModel

def valid_answers():
    return {
        "Height (cm)": 170,
        "Weight (kg)": 70,
        "BMI": 24.2,
        "Cholesterol Level (mg/dL)": 180,
        "Blood Glucose Level (mg/dL)": 95,
        "Stress Levels": 4,
        "Vision Sharpness": 1.0,
        "Hearing Ability (dB)": 20,
        "Bone Density (g/cm²)": 1.1,
        "BP_Systolic": 120,
        "BP_Diastolic": 80,
    }


def _process_task_like_worker(task_external_id: str, session: Session, worker_id: str = "test-worker") -> None:
    """
    Повторяет бизнес-логику worker (без RabbitMQ):
      - load task
      - validate
      - can_pay
      - start_processing
      - predict
      - charge_after_success
      - set_result DONE
    """
    billing = BillingService(session)

    task = task_crud.get_task_by_external_id(task_external_id, session)
    if task is None:
        raise ValueError(f"Task not found for task_id={task_external_id}")

    if task.status in {TaskStatus.DONE, TaskStatus.FAILED}:
        return

    meta = ml_model_crud.get_model_by_id(task.model_id, session)
    if meta is None:
        task.worker_id = worker_id
        task.set_error("ML модель не найдена")
        task_crud.update_task(task, session)
        return

    runtime = RuntimeMLModel(meta=meta)
    features = dict(task.answers or {})

    ok, errors_obj = runtime.validate(features)
    errors = [{"field_name": getattr(e, "field_name", "unknown"), "message": getattr(e, "message", str(e))} for e in errors_obj]

    if errors:
        task.validation_errors = errors
        task.worker_id = worker_id
        task.set_error("Validation failed in worker")
        task_crud.update_task(task, session)
        return

    price = int(meta.price_per_task)

    if not billing.can_pay(task.user_id, price):
        task.worker_id = worker_id
        task.set_error("Недостаточно средств")
        task.status = TaskStatus.FAILED  # CHANGED: фиксируем FAILED, чтобы соответствовало сценарию
        task_crud.update_task(task, session)
        return

    try:
        if task.status == TaskStatus.VALIDATED:
            task.start_processing()
        task.worker_id = worker_id
        task_crud.update_task(task, session)

        result = runtime.predict(features)

        if task.charged_amount is None:
            billing.charge_after_success(task.user_id, price, task.id)

        task.set_result(result, charged_amount=price)
        task.worker_id = worker_id
        task_crud.update_task(task, session)

    except Exception as ex:  
        task.worker_id = worker_id
        task.set_error(f"Predict failed: {ex}")
        task.status = TaskStatus.FAILED
        task_crud.update_task(task, session)
        return


def test_e2e_predict_then_worker_charges_and_sets_done(client, session: Session):
    email = "e2e@test.com"
    password = "StrongPass123"

    assert register_user(client, email, password).status_code == 201
    token = login_user(client, email, password).json()["access_token"]
    headers = auth_headers(token)

    client.post("/api/wallet/topup", headers=headers, json={"amount": 200})
    bal_before = client.get("/api/wallet/balance", headers=headers).json()["balance"]

    r = client.post("/api/tasks/predict", headers=headers, json={"model_id": 1, "answers": valid_answers()})
    assert r.status_code == 202, r.text
    task_id = r.json()["task_id"]

    # имитируем обработку воркером
    _process_task_like_worker(task_id, session)

    # проверяем задачу через API
    t = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert t.status_code == 200, t.text
    task = t.json()
    assert task["status"] == TaskStatus.DONE.value
    assert task.get("charged_amount") == 25  

    # проверяем баланс: списалось ровно 25
    bal_after = client.get("/api/wallet/balance", headers=headers).json()["balance"]
    assert bal_after == bal_before - 25

    # проверяем наличие CHARGE транзакции
    hist = client.get("/api/wallet/transactions", headers=headers).json()["items"]
    assert any(i.get("tx_type") == TransactionType.CHARGE.value for i in hist), hist


def test_worker_denies_charge_when_insufficient_balance(client, session: Session):  
    email = "lowbalance@test.com"
    password = "StrongPass123"

    assert register_user(client, email, password).status_code == 201
    token = login_user(client, email, password).json()["access_token"]
    headers = auth_headers(token)

    # кладём меньше, чем price_per_task=25
    client.post("/api/wallet/topup", headers=headers, json={"amount": 10})
    bal_before = client.get("/api/wallet/balance", headers=headers).json()["balance"]

    r = client.post("/api/tasks/predict", headers=headers, json={"model_id": 1, "answers": valid_answers()})

    assert r.status_code == 202, r.text
    task_id = r.json()["task_id"]

    _process_task_like_worker(task_id, session)

    t = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert t.status_code == 200, t.text
    task = t.json()
    assert task["status"] == TaskStatus.FAILED.value

    # баланс не изменился
    bal_after = client.get("/api/wallet/balance", headers=headers).json()["balance"]
    assert bal_after == bal_before

    # списания нет
    hist = client.get("/api/wallet/transactions", headers=headers).json()["items"]
    assert not any(i.get("tx_type") == TransactionType.CHARGE.value for i in hist), hist


def test_worker_no_charge_when_predict_crashes(client, session: Session, monkeypatch):  
    email = "crash@test.com"
    password = "StrongPass123"

    assert register_user(client, email, password).status_code == 201
    token = login_user(client, email, password).json()["access_token"]
    headers = auth_headers(token)

    client.post("/api/wallet/topup", headers=headers, json={"amount": 200})
    bal_before = client.get("/api/wallet/balance", headers=headers).json()["balance"]

    r = client.post("/api/tasks/predict", headers=headers, json={"model_id": 1, "answers": valid_answers()})
    assert r.status_code == 202, r.text
    task_id = r.json()["task_id"]

    # monkeypatch: ломаем predict
    def boom(self, features):
        raise RuntimeError("Synthetic predict error")

    monkeypatch.setattr(RuntimeMLModel, "predict", boom)

    _process_task_like_worker(task_id, session)

    t = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert t.status_code == 200, t.text
    task = t.json()
    assert task["status"] == TaskStatus.FAILED.value

    # баланс не должен измениться
    bal_after = client.get("/api/wallet/balance", headers=headers).json()["balance"]
    assert bal_after == bal_before

    # списания нет
    hist = client.get("/api/wallet/transactions", headers=headers).json()["items"]
    assert not any(i.get("tx_type") == TransactionType.CHARGE.value for i in hist), hist

