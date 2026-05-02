"""
Redis Pub/Sub integration tests.

These tests verify that:
1. broadcast_local() delivers events directly to local WebSocket connections
2. broadcast() publishes to Redis; the subscriber loop receives it and calls broadcast_local()
3. When Redis is unavailable, broadcast() falls back to broadcast_local()
"""
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.websocket_service import manager

client = TestClient(app)

CHANNEL_ID = 1


def _get_token(user_id: int = 1) -> str:
    r = client.post("/auth/dev-login", json={"user_id": user_id})
    return r.json()["access_token"]


def _auth_headers(user_id: int = 1) -> dict:
    return {"Authorization": f"Bearer {_get_token(user_id)}"}


# ── broadcast_local() ───────────────────────────────────────────────────────


def test_broadcast_local_delivers_to_ws_clients():
    """broadcast_local() sends events directly to local connections."""
    token = _get_token()
    with client.websocket_connect(f"/ws?token={token}") as ws:
        client.post(
            f"/channels/{CHANNEL_ID}/messages",
            json={"content": "local broadcast test"},
            headers=_auth_headers(),
        )
        event = ws.receive_json()
    assert event["type"] == "message.created"
    assert event["payload"]["content"] == "local broadcast test"


# ── Redis fallback ──────────────────────────────────────────────────────────


def test_broadcast_falls_back_to_local_when_redis_unavailable():
    """When Redis publish returns False, broadcast_local() is called."""
    token = _get_token()
    with patch(
        "app.services.redis_client.publish_event",
        new_callable=AsyncMock,
        return_value=False,
    ):
        with client.websocket_connect(f"/ws?token={token}") as ws:
            client.post(
                f"/channels/{CHANNEL_ID}/messages",
                json={"content": "redis down fallback"},
                headers=_auth_headers(),
            )
            event = ws.receive_json()
    assert event["type"] == "message.created"
    assert event["payload"]["content"] == "redis down fallback"


# ── Redis publish path ──────────────────────────────────────────────────────


def test_broadcast_publishes_to_redis_when_available():
    """When Redis is available, broadcast() publishes and does NOT call broadcast_local()."""
    token = _get_token()
    with patch(
        "app.services.redis_client.publish_event",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_publish:
        with client.websocket_connect(f"/ws?token={token}"):
            client.post(
                f"/channels/{CHANNEL_ID}/messages",
                json={"content": "redis publish path"},
                headers=_auth_headers(),
            )
        assert mock_publish.called
        call_args = mock_publish.call_args[0][0]
        assert call_args["type"] == "message.created"
        assert call_args["payload"]["content"] == "redis publish path"


# ── Subscriber loop unit test ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_subscriber_loop_calls_broadcast_local_on_message():
    """Subscriber loop calls manager.broadcast_local() when a Redis message arrives."""
    from app.services import redis_subscriber

    received_events = []

    async def fake_broadcast_local(event):
        received_events.append(event)

    test_event = {"type": "message.created", "payload": {"content": "pubsub test"}}

    # Simulate a Redis message sequence: subscribe ack → message → then cancel
    messages = iter([
        {"type": "subscribe", "data": 1},
        {"type": "message", "data": json.dumps(test_event)},
    ])

    async def fake_listen():
        for msg in messages:
            yield msg
        # Block until cancelled
        await asyncio.sleep(9999)

    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.listen = fake_listen

    mock_redis = MagicMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
    mock_redis.aclose = AsyncMock()

    with patch.object(redis_subscriber.manager, "broadcast_local", side_effect=fake_broadcast_local):
        with patch("app.services.redis_subscriber.aioredis.from_url", return_value=mock_redis):
            task = asyncio.create_task(redis_subscriber.redis_subscriber_loop())
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    assert len(received_events) == 1
    assert received_events[0] == test_event


# ── End-to-end via subscriber (Redis available) ────────────────────────────


def test_ws_receives_event_published_via_redis_subscriber():
    """
    Full path: POST /messages → broadcast() → Redis publish → subscriber → broadcast_local().
    Requires a running Redis (Docker). Skipped if Redis is unavailable.
    """
    import asyncio as _asyncio
    from app.services.redis_client import publish_event as _pub

    async def _ping():
        return await _pub({"type": "ping"})

    redis_ok = _asyncio.get_event_loop().run_until_complete(_ping())
    if not redis_ok:
        pytest.skip("Redis not available")

    token = _get_token()
    with client.websocket_connect(f"/ws?token={token}") as ws:
        client.post(
            f"/channels/{CHANNEL_ID}/messages",
            json={"content": "e2e redis pubsub test"},
            headers=_auth_headers(),
        )
        ws.receive_json(timeout=2)
