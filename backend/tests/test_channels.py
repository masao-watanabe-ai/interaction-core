from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

INITIAL_CHANNEL_NAMES = {"general", "random", "ai-analysis"}


def test_list_channels_ok():
    response = client.get("/channels")
    assert response.status_code == 200


def test_list_channels_returns_initial_channels():
    response = client.get("/channels")
    names = {ch["name"] for ch in response.json()}
    assert INITIAL_CHANNEL_NAMES.issubset(names)


def test_create_channel():
    response = client.post("/channels", json={"name": "step3-new"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "step3-new"
    assert data["workspace_id"] == 1
    assert isinstance(data["id"], int)


def test_created_channel_appears_in_list():
    client.post("/channels", json={"name": "step3-listed"})
    response = client.get("/channels")
    names = [ch["name"] for ch in response.json()]
    assert "step3-listed" in names


def test_create_duplicate_channel_returns_409():
    client.post("/channels", json={"name": "step3-dup"})
    response = client.post("/channels", json={"name": "step3-dup"})
    assert response.status_code == 409
