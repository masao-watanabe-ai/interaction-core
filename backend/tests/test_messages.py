from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

CHANNEL_ID = 1
MISSING_CHANNEL_ID = 9999


def _auth_headers(user_id: int = 1) -> dict:
    r = client.post("/auth/dev-login", json={"user_id": user_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_post_message():
    response = client.post(
        f"/channels/{CHANNEL_ID}/messages",
        json={"content": "Hello world"},
        headers=_auth_headers(),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Hello world"
    assert data["channel_id"] == CHANNEL_ID
    assert data["user_id"] == 1
    assert isinstance(data["id"], int)
    assert "created_at" in data


def test_get_messages():
    client.post(
        f"/channels/{CHANNEL_ID}/messages",
        json={"content": "msg-for-get"},
        headers=_auth_headers(),
    )
    response = client.get(f"/channels/{CHANNEL_ID}/messages")
    assert response.status_code == 200
    contents = [m["content"] for m in response.json()]
    assert "msg-for-get" in contents


def test_get_messages_ascending_order():
    headers = _auth_headers()
    r1 = client.post(f"/channels/{CHANNEL_ID}/messages", json={"content": "order-first"}, headers=headers)
    r2 = client.post(f"/channels/{CHANNEL_ID}/messages", json={"content": "order-second"}, headers=headers)
    id1, id2 = r1.json()["id"], r2.json()["id"]

    response = client.get(f"/channels/{CHANNEL_ID}/messages")
    ids = [m["id"] for m in response.json()]
    assert ids.index(id1) < ids.index(id2)


def test_empty_content_returns_422():
    response = client.post(
        f"/channels/{CHANNEL_ID}/messages",
        json={"content": ""},
        headers=_auth_headers(),
    )
    assert response.status_code == 422


def test_whitespace_content_returns_422():
    response = client.post(
        f"/channels/{CHANNEL_ID}/messages",
        json={"content": "   "},
        headers=_auth_headers(),
    )
    assert response.status_code == 422


def test_content_too_long_returns_422():
    response = client.post(
        f"/channels/{CHANNEL_ID}/messages",
        json={"content": "x" * 2001},
        headers=_auth_headers(),
    )
    assert response.status_code == 422


def test_post_without_auth_returns_401():
    response = client.post(f"/channels/{CHANNEL_ID}/messages", json={"content": "Hello"})
    assert response.status_code == 401


def test_post_to_nonexistent_channel_returns_404():
    response = client.post(
        f"/channels/{MISSING_CHANNEL_ID}/messages",
        json={"content": "Hello"},
        headers=_auth_headers(),
    )
    assert response.status_code == 404


def test_get_from_nonexistent_channel_returns_404():
    response = client.get(f"/channels/{MISSING_CHANNEL_ID}/messages")
    assert response.status_code == 404


def test_limit_param():
    headers = _auth_headers()
    for i in range(5):
        client.post(f"/channels/{CHANNEL_ID}/messages", json={"content": f"limit-{i}"}, headers=headers)
    response = client.get(f"/channels/{CHANNEL_ID}/messages?limit=3")
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_before_id_param():
    headers = _auth_headers()
    r1 = client.post(f"/channels/{CHANNEL_ID}/messages", json={"content": "before-A"}, headers=headers)
    r2 = client.post(f"/channels/{CHANNEL_ID}/messages", json={"content": "before-B"}, headers=headers)
    pivot_id = r2.json()["id"]

    response = client.get(f"/channels/{CHANNEL_ID}/messages?before_id={pivot_id}")
    assert response.status_code == 200
    ids = [m["id"] for m in response.json()]
    assert all(i < pivot_id for i in ids)
    assert r1.json()["id"] in ids
