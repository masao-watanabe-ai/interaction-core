from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

CHANNEL_ID = 1
MISSING_CHANNEL_ID = 9999


def _auth_headers(user_id: int = 1) -> dict:
    r = client.post("/auth/dev-login", json={"user_id": user_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _run_worker(channel_id: int) -> None:
    """Helper: run the analysis worker synchronously (bypasses RQ queue)."""
    from app.worker.analysis_worker import run_analysis_job
    run_analysis_job(channel_id)


# ── POST /analysis/channels/{id} ────────────────────────────────────────────


def test_post_analysis_returns_queued():
    with patch("app.routes.analysis.enqueue_analysis"):
        response = client.post(f"/analysis/channels/{CHANNEL_ID}")
    assert response.status_code == 202
    assert response.json() == {"status": "queued"}


def test_post_analysis_enqueues_with_correct_channel_id():
    with patch("app.routes.analysis.enqueue_analysis") as mock_enqueue:
        client.post(f"/analysis/channels/{CHANNEL_ID}")
    mock_enqueue.assert_called_once_with(CHANNEL_ID)


def test_post_analysis_nonexistent_channel_returns_404():
    response = client.post(f"/analysis/channels/{MISSING_CHANNEL_ID}")
    assert response.status_code == 404


def test_post_analysis_queue_unavailable_returns_503():
    with patch("app.routes.analysis.enqueue_analysis", side_effect=Exception("Redis down")):
        response = client.post(f"/analysis/channels/{CHANNEL_ID}")
    assert response.status_code == 503


# ── GET /analysis/channels/{id}/summary ─────────────────────────────────────


def test_get_summary_returns_latest_analysis():
    _run_worker(CHANNEL_ID)
    response = client.get(f"/analysis/channels/{CHANNEL_ID}/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["channel_id"] == CHANNEL_ID
    assert "analyzed_at" in data
    assert isinstance(data["total_messages"], int)
    assert isinstance(data["top_keywords"], list)


def test_get_summary_nonexistent_channel_returns_404():
    response = client.get(f"/analysis/channels/{MISSING_CHANNEL_ID}/summary")
    assert response.status_code == 404


def test_get_summary_channel_without_analysis_returns_404():
    r = client.post("/channels", json={"name": "no-analysis-yet"})
    ch_id = r.json()["id"]
    response = client.get(f"/analysis/channels/{ch_id}/summary")
    assert response.status_code == 404
