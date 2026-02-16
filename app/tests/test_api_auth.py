from tests.helpers import register_user, login_user

def test_register_and_login_ok(client):
    email = "user1@test.com"
    password = "StrongPass123"

    r = register_user(client, email, password)
    assert r.status_code in (200, 201), r.text

    r2 = login_user(client, email, password)
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"


def test_login_wrong_password(client):
    email = "user2@test.com"
    password = "StrongPass123"

    assert register_user(client, email, password).status_code in (200, 201)
    bad = login_user(client, email, "WrongPass123")
    assert bad.status_code in (401, 403), bad.text
