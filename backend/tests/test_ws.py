import pytest
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

CHANNEL_ID = 1


def _get_token(user_id: int = 1) -> str:
    r = client.post("/auth/dev-login", json={"user_id": user_id})
    return r.json()["access_token"]


def _auth_headers(user_id: int = 1) -> dict:
    return {"Authorization": f"Bearer {_get_token(user_id)}"}


# ── query token 認証（既存テスト） ────────────────────────────────────

def test_ws_connect_with_valid_token():
    token = _get_token()
    with client.websocket_connect(f"/ws?token={token}"):
        pass  # 接続確立・切断でエラーなし


def test_ws_connect_with_invalid_token_is_rejected():
    with client.websocket_connect("/ws?token=invalid.token.here") as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 4001


def test_ws_receives_message_created_event():
    token = _get_token()

    with client.websocket_connect(f"/ws?token={token}") as ws:
        # HTTP POST でメッセージ投稿 → broadcast が await されてからレスポンスが返る
        response = client.post(
            f"/channels/{CHANNEL_ID}/messages",
            json={"content": "hello from ws test"},
            headers=_auth_headers(),
        )
        assert response.status_code == 201

        # broadcast 済みなので receive_json() ですぐ取れる
        event = ws.receive_json()

        assert event["type"] == "message.created"
        assert event["payload"]["content"] == "hello from ws test"
        assert event["payload"]["channel_id"] == CHANNEL_ID
        assert isinstance(event["payload"]["id"], int)
        assert "created_at" in event["payload"]


def test_ws_does_not_receive_event_after_disconnect():
    token = _get_token()

    with client.websocket_connect(f"/ws?token={token}"):
        pass

    # 切断後に投稿しても broadcast はエラーなく完了する（dead 接続をスキップ）
    response = client.post(
        f"/channels/{CHANNEL_ID}/messages",
        json={"content": "post after disconnect"},
        headers=_auth_headers(),
    )
    assert response.status_code == 201


def test_ws_multiple_clients_all_receive_event():
    token = _get_token()

    with client.websocket_connect(f"/ws?token={token}") as ws1:
        with client.websocket_connect(f"/ws?token={token}") as ws2:
            client.post(
                f"/channels/{CHANNEL_ID}/messages",
                json={"content": "broadcast to all"},
                headers=_auth_headers(),
            )
            e1 = ws1.receive_json()
            e2 = ws2.receive_json()

    assert e1["type"] == "message.created"
    assert e2["type"] == "message.created"
    assert e1["payload"]["content"] == "broadcast to all"
    assert e2["payload"]["content"] == "broadcast to all"


# ── Cookie 認証（新規テスト） ─────────────────────────────────────────

def test_ws_connect_with_cookie():
    token = _get_token()
    with client.websocket_connect("/ws", headers={"cookie": f"access_token={token}"}):
        pass


def test_ws_connect_without_any_auth_is_rejected():
    with client.websocket_connect("/ws") as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 4001


def test_ws_connect_with_invalid_cookie_is_rejected():
    with client.websocket_connect("/ws", headers={"cookie": "access_token=invalid.jwt.value"}) as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 4001


def test_ws_cookie_auth_receives_message_created_event():
    token = _get_token()

    with client.websocket_connect("/ws", headers={"cookie": f"access_token={token}"}) as ws:
        response = client.post(
            f"/channels/{CHANNEL_ID}/messages",
            json={"content": "cookie auth ws test"},
            headers=_auth_headers(),
        )
        assert response.status_code == 201

        event = ws.receive_json()
        assert event["type"] == "message.created"
        assert event["payload"]["content"] == "cookie auth ws test"
        assert event["payload"]["channel_id"] == CHANNEL_ID


def test_ws_query_token_takes_precedence_over_cookie():
    token = _get_token()
    # 両方提供した場合でも接続できる（query token が優先）
    with client.websocket_connect(
        f"/ws?token={token}",
        headers={"cookie": f"access_token={token}"},
    ):
        pass


def test_ws_valid_cookie_invalid_query_token_is_rejected():
    token = _get_token()
    # query token が不正なら Cookie があっても 4001（query が優先）
    with client.websocket_connect(
        "/ws?token=invalid.token",
        headers={"cookie": f"access_token={token}"},
    ) as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 4001
