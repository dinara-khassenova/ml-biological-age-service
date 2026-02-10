from fastapi.testclient import TestClient


def register_user(client: TestClient, email: str, password: str, role: str = "USER"):
    return client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "role": role},
    )


def login_user(client: TestClient, email: str, password: str):
    return client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
