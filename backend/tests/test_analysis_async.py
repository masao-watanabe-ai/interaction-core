"""
Step 14 — Async analysis tests.

Tests:
  1. Worker processes correctly (stores analysis in DB)
  2. Worker publishes analysis.completed event with correct payload
  3. Emotion / keyword detection via worker
  4. Worker handles empty channel without error
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.worker.analysis_worker import run_analysis_job

client = TestClient(app)

CHANNEL_ID = 1


def _auth_headers(user_id: int = 1) -> dict:
    r = client.post("/auth/dev-login", json={"user_id": user_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── Worker: stores analysis ──────────────────────────────────────────────────


def test_worker_stores_analysis_in_db():
    run_analysis_job(CHANNEL_ID)
    response = client.get(f"/analysis/channels/{CHANNEL_ID}/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["channel_id"] == CHANNEL_ID
    assert isinstance(data["total_messages"], int)
    assert isinstance(data["top_keywords"], list)
    assert "analyzed_at" in data


def test_worker_empty_channel_does_not_crash():
    r = client.post("/channels", json={"name": "worker-empty-test"})
    ch_id = r.json()["id"]
    run_analysis_job(ch_id)
    response = client.get(f"/analysis/channels/{ch_id}/summary")
    assert response.status_code == 200
    assert response.json()["total_messages"] == 0
    assert response.json()["top_keywords"] == []


def test_worker_nonexistent_channel_does_not_crash():
    # Should complete without exception (no analysis stored)
    run_analysis_job(99999)


# ── Worker: publishes event ──────────────────────────────────────────────────


def test_worker_publishes_analysis_completed_event():
    published: list[tuple] = []

    mock_redis = MagicMock()
    mock_redis.publish = AsyncMock(side_effect=lambda ch, data: published.append((ch, data)))
    mock_redis.aclose = AsyncMock()

    with patch("app.worker.analysis_worker.aioredis.from_url", return_value=mock_redis):
        run_analysis_job(CHANNEL_ID)

    assert len(published) == 1
    channel, raw = published[0]
    assert channel == "chat_events"

    event = json.loads(raw)
    assert event["type"] == "analysis.completed"
    payload = event["payload"]
    assert payload["channel_id"] == CHANNEL_ID
    result = payload["result"]
    assert "total_messages" in result
    assert "top_keywords" in result
    assert "positive_count" in result
    assert "negative_count" in result
    assert "question_count" in result
    assert "active_users" in result
    assert "summary_text" in result
    assert "insights" in result
    assert "suggested_actions" in result
    assert "analyzed_at" in result
    assert isinstance(result["insights"], list)
    assert isinstance(result["suggested_actions"], list)


def test_worker_no_event_published_for_missing_channel():
    mock_redis = MagicMock()
    mock_redis.publish = AsyncMock()
    mock_redis.aclose = AsyncMock()

    with patch("app.worker.analysis_worker.aioredis.from_url", return_value=mock_redis):
        run_analysis_job(99999)

    mock_redis.publish.assert_not_called()


# ── Emotion / keyword detection via worker ───────────────────────────────────


def test_worker_positive_emotion_detection():
    headers = _auth_headers()
    r = client.post("/channels", json={"name": "worker-pos-test"})
    ch_id = r.json()["id"]
    client.post(f"/channels/{ch_id}/messages", json={"content": "すごい！ありがとう"}, headers=headers)
    run_analysis_job(ch_id)
    data = client.get(f"/analysis/channels/{ch_id}/summary").json()
    assert data["positive_count"] >= 1


def test_worker_negative_emotion_detection():
    headers = _auth_headers()
    r = client.post("/channels", json={"name": "worker-neg-test"})
    ch_id = r.json()["id"]
    client.post(f"/channels/{ch_id}/messages", json={"content": "エラーが問題になっている"}, headers=headers)
    run_analysis_job(ch_id)
    data = client.get(f"/analysis/channels/{ch_id}/summary").json()
    assert data["negative_count"] >= 1


def test_worker_question_detection():
    headers = _auth_headers()
    r = client.post("/channels", json={"name": "worker-question-test"})
    ch_id = r.json()["id"]
    client.post(f"/channels/{ch_id}/messages", json={"content": "どうすればいいですか？"}, headers=headers)
    run_analysis_job(ch_id)
    data = client.get(f"/analysis/channels/{ch_id}/summary").json()
    assert data["question_count"] >= 1


# ── WS: analysis.completed event delivered via subscriber ────────────────────


def test_ws_receives_analysis_completed_event():
    """End-to-end: worker publishes → Redis subscriber → WebSocket client."""
    import asyncio as _asyncio
    from app.services.redis_client import publish_event

    async def _ping():
        return await publish_event({"type": "ping"})

    redis_ok = _asyncio.get_event_loop().run_until_complete(_ping())
    if not redis_ok:
        import pytest
        pytest.skip("Redis not available")

    token_r = client.post("/auth/dev-login", json={"user_id": 1})
    token = token_r.json()["access_token"]

    with client.websocket_connect(f"/ws?token={token}") as ws:
        run_analysis_job(CHANNEL_ID)
        event = ws.receive_json(timeout=3)

    assert event["type"] == "analysis.completed"
    assert event["payload"]["channel_id"] == CHANNEL_ID
    assert "result" in event["payload"]


# ── LLM integration in worker ────────────────────────────────────────────────


def _mock_llm_result():
    from app.services.llm_service import LLMAnalysisResult
    return LLMAnalysisResult(
        summary_text="LLMによる自然言語サマリーです。",
        insights=["重要ポイント1", "重要ポイント2"],
        suggested_actions=["アクション1", "アクション2"],
    )


def test_worker_uses_llm_result_when_available():
    """Worker stores LLM summary/insights/actions in DB."""
    headers = _auth_headers()
    r = client.post("/channels", json={"name": "worker-llm-test"})
    ch_id = r.json()["id"]
    client.post(f"/channels/{ch_id}/messages", json={"content": "テスト"}, headers=headers)

    mock_redis = MagicMock()
    mock_redis.publish = AsyncMock()
    mock_redis.aclose = AsyncMock()

    with patch("app.worker.analysis_worker.aioredis.from_url", return_value=mock_redis):
        with patch(
            "app.worker.analysis_worker.analyze_with_llm",
            new_callable=AsyncMock,
            return_value=_mock_llm_result(),
        ):
            run_analysis_job(ch_id)

    data = client.get(f"/analysis/channels/{ch_id}/summary").json()
    assert data["summary_text"] == "LLMによる自然言語サマリーです。"
    assert data["insights"] == ["重要ポイント1", "重要ポイント2"]
    assert data["suggested_actions"] == ["アクション1", "アクション2"]


def test_worker_falls_back_to_rule_based_when_llm_unavailable():
    """When analyze_with_llm returns None, rule-based summary is used."""
    headers = _auth_headers()
    r = client.post("/channels", json={"name": "worker-fallback-test"})
    ch_id = r.json()["id"]
    client.post(f"/channels/{ch_id}/messages", json={"content": "テスト"}, headers=headers)

    mock_redis = MagicMock()
    mock_redis.publish = AsyncMock()
    mock_redis.aclose = AsyncMock()

    with patch("app.worker.analysis_worker.aioredis.from_url", return_value=mock_redis):
        with patch(
            "app.worker.analysis_worker.analyze_with_llm",
            new_callable=AsyncMock,
            return_value=None,
        ):
            run_analysis_job(ch_id)

    data = client.get(f"/analysis/channels/{ch_id}/summary").json()
    assert data["summary_text"] != ""    # rule-based summary is present
    assert data["insights"] == []        # no LLM insights
    assert data["suggested_actions"] == []


def test_worker_event_includes_llm_fields():
    """Published event contains insights and suggested_actions from LLM."""
    published: list[tuple] = []

    mock_redis = MagicMock()
    mock_redis.publish = AsyncMock(side_effect=lambda ch, data: published.append((ch, data)))
    mock_redis.aclose = AsyncMock()

    with patch("app.worker.analysis_worker.aioredis.from_url", return_value=mock_redis):
        with patch(
            "app.worker.analysis_worker.analyze_with_llm",
            new_callable=AsyncMock,
            return_value=_mock_llm_result(),
        ):
            run_analysis_job(CHANNEL_ID)

    event = json.loads(published[0][1])
    result = event["payload"]["result"]
    assert result["insights"] == ["重要ポイント1", "重要ポイント2"]
    assert result["suggested_actions"] == ["アクション1", "アクション2"]
    assert result["summary_text"] == "LLMによる自然言語サマリーです。"
