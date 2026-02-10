from tests.helpers import register_user, login_user, auth_headers


def test_balance_topup_and_transactions_history(client):
    email = "wallet@test.com"
    password = "StrongPass123"

    assert register_user(client, email, password).status_code in (200, 201)
    token = login_user(client, email, password).json()["access_token"]
    headers = auth_headers(token)

    b1 = client.get("/api/wallet/balance", headers=headers)
    assert b1.status_code == 200, b1.text
    start_balance = b1.json()["balance"]

    top = client.post("/api/wallet/topup", headers=headers, json={"amount": 100})
    assert top.status_code in (200, 201), top.text
    assert top.json()["amount"] == 100

    b2 = client.get("/api/wallet/balance", headers=headers)
    assert b2.status_code == 200, b2.text
    assert b2.json()["balance"] == start_balance + 100

    hist = client.get("/api/wallet/transactions", headers=headers)
    assert hist.status_code == 200, hist.text
    items = hist.json()["items"]
    assert any(i.get("amount") == 100 for i in items)
