from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_dev_login_returns_token():
    response = client.post("/auth/dev-login", json={"user_id": 1})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


def test_dev_login_nonexistent_user_returns_404():
    response = client.post("/auth/dev-login", json={"user_id": 9999})
    assert response.status_code == 404


def test_get_me_returns_user():
    login = client.post("/auth/dev-login", json={"user_id": 1})
    token = login.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["email"] == "demo@example.com"
    assert data["display_name"] == "Demo User"


def test_get_me_without_token_returns_401():
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_get_me_with_invalid_token_returns_401():
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401


def test_get_me_with_tampered_token_returns_401():
    login = client.post("/auth/dev-login", json={"user_id": 1})
    token = login.json()["access_token"]
    tampered = token[:-5] + "XXXXX"

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert response.status_code == 401
