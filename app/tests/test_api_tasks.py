
from tests.helpers import register_user, login_user, auth_headers

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


def test_predict_creates_task_and_no_immediate_charge(client):
    email = "task@test.com"
    password = "StrongPass123"

    assert register_user(client, email, password).status_code in (200, 201)
    token = login_user(client, email, password).json()["access_token"]
    headers = auth_headers(token)

    client.post("/api/wallet/topup", headers=headers, json={"amount": 100})
    b1 = client.get("/api/wallet/balance", headers=headers).json()["balance"]


    payload = {"model_id": 1, "answers": valid_answers()}
    r = client.post("/api/tasks/predict", headers=headers, json=payload)
    assert r.status_code == 202, r.text  

    task_id = r.json().get("task_id")
    assert task_id, r.text

    b2 = client.get("/api/wallet/balance", headers=headers).json()["balance"]
    assert b2 == b1


def test_predict_invalid_model_returns_404_and_no_charge(client):
    email = "taskbad@test.com"
    password = "StrongPass123"

    assert register_user(client, email, password).status_code in (200, 201)
    token = login_user(client, email, password).json()["access_token"]
    headers = auth_headers(token)

    client.post("/api/wallet/topup", headers=headers, json={"amount": 100})
    b1 = client.get("/api/wallet/balance", headers=headers).json()["balance"]

    r = client.post(
        "/api/tasks/predict",
        headers=headers,
        json={"model_id": 999999, "answers": {}},
        )
    assert r.status_code == 404, r.text

    b2 = client.get("/api/wallet/balance", headers=headers).json()["balance"]
    assert b2 == b1


def test_predict_validation_error_422_and_no_charge(client):
    email = "task422@test.com"
    password = "StrongPass123"

    assert register_user(client, email, password).status_code in (200, 201)
    token = login_user(client, email, password).json()["access_token"]
    headers = auth_headers(token)

    client.post("/api/wallet/topup", headers=headers, json={"amount": 100})
    b1 = client.get("/api/wallet/balance", headers=headers).json()["balance"]

    r = client.post("/api/tasks/predict", headers=headers, json={"model_id": 1, "answers": {}})
    assert r.status_code == 422, r.text

    detail = r.json().get("detail")
    assert isinstance(detail, dict), r.text
    assert "task_id" in detail, r.text
    assert "validation_errors" in detail, r.text

    b2 = client.get("/api/wallet/balance", headers=headers).json()["balance"]
    assert b2 == b1


def test_tasks_history_contains_created_task(client):
    email = "history@test.com"
    password = "StrongPass123"

    assert register_user(client, email, password).status_code in (200, 201)
    token = login_user(client, email, password).json()["access_token"]
    headers = auth_headers(token)

    client.post("/api/wallet/topup", headers=headers, json={"amount": 100})

    r = client.post("/api/tasks/predict", headers=headers, json={"model_id": 1, "answers": valid_answers()})
    assert r.status_code == 202, r.text
    task_id = r.json()["task_id"]

    h = client.get("/api/tasks/history", headers=headers)
    assert h.status_code == 200, h.text
    items = h.json()

    assert any(i.get("external_id") == task_id or i.get("task_id") == task_id for i in items), items

