from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.routes.auth import create_oauth_state, verify_oauth_state

client = TestClient(app, follow_redirects=False)


# ── state JWT ────────────────────────────────────────────────────────

def test_create_and_verify_state():
    state = create_oauth_state()
    assert verify_oauth_state(state) is True


def test_verify_invalid_state():
    assert verify_oauth_state("not-a-valid-jwt") is False


def test_verify_tampered_state():
    state = create_oauth_state()
    assert verify_oauth_state(state[:-4] + "XXXX") is False


# ── /auth/google ─────────────────────────────────────────────────────

def test_google_login_without_config_returns_501():
    with patch.object(settings, "google_client_id", ""):
        response = client.get("/auth/google")
    assert response.status_code == 501


def test_google_login_redirects_to_google():
    with patch.object(settings, "google_client_id", "test-client-id"):
        response = client.get("/auth/google")
    assert response.status_code in (302, 307)
    assert "accounts.google.com" in response.headers["location"]
    assert "state=" in response.headers["location"]


# ── /auth/google/callback ────────────────────────────────────────────

def test_callback_invalid_state_returns_400():
    response = client.get("/auth/google/callback?code=abc&state=bad-state")
    assert response.status_code == 400


def _mock_callback(state: str, email: str, sub: str):
    """callback をモックして呼び出し、レスポンスを返す"""
    mock_token = {"access_token": "mock-google-token"}
    mock_userinfo = {
        "sub": sub,
        "email": email,
        "name": "Test User",
        "picture": "https://example.com/pic.jpg",
    }
    with (
        patch("app.routes.auth.exchange_code_for_token", new_callable=AsyncMock, return_value=mock_token),
        patch("app.routes.auth.get_google_userinfo", new_callable=AsyncMock, return_value=mock_userinfo),
        patch.object(settings, "google_client_id", "test-id"),
        patch.object(settings, "google_client_secret", "test-secret"),
    ):
        return client.get(f"/auth/google/callback?code=test-code&state={state}")


def test_callback_sets_httponly_cookie():
    state = create_oauth_state()
    response = _mock_callback(state, "cookie_set_test@example.com", "google-sub-cookie-test")

    assert response.status_code in (302, 307)
    # JWT が URL に露出しない
    assert "token=" not in response.headers["location"]
    # HttpOnly Cookie が設定される
    assert "access_token" in response.cookies
    # Set-Cookie ヘッダーに HttpOnly が含まれる
    set_cookie = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()


def test_callback_redirects_to_frontend_without_token_in_url():
    state = create_oauth_state()
    response = _mock_callback(state, "redirect_test@example.com", "google-sub-redirect")

    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert location == settings.frontend_url
    assert "token=" not in location


def test_callback_creates_new_user():
    state = create_oauth_state()
    response = _mock_callback(state, "newuser_oauth@example.com", "google-uid-new-999")

    assert response.status_code in (302, 307)
    assert "access_token" in response.cookies


def test_callback_links_existing_user_by_email():
    state = create_oauth_state()
    # demo@example.com は seed ユーザーとして存在
    response = _mock_callback(state, "demo@example.com", "google-uid-demo-linked")

    assert response.status_code in (302, 307)
    assert "access_token" in response.cookies


def test_callback_google_api_failure_returns_400():
    state = create_oauth_state()
    with (
        patch("app.routes.auth.exchange_code_for_token", new_callable=AsyncMock, side_effect=Exception("network error")),
        patch.object(settings, "google_client_id", "test-id"),
        patch.object(settings, "google_client_secret", "test-secret"),
    ):
        response = client.get(f"/auth/google/callback?code=bad-code&state={state}")

    assert response.status_code == 400


# ── /auth/me Cookie 認証 ──────────────────────────────────────────────

def test_get_me_with_cookie_auth():
    token = client.post("/auth/dev-login", json={"user_id": 1}).json()["access_token"]
    response = client.get("/auth/me", cookies={"access_token": token})
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_get_me_bearer_takes_precedence_over_cookie():
    token = client.post("/auth/dev-login", json={"user_id": 1}).json()["access_token"]
    # Bearer と Cookie を両方送った場合、Bearer が優先される
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        cookies={"access_token": token},
    )
    assert response.status_code == 200


def test_get_me_invalid_cookie_returns_401():
    response = client.get("/auth/me", cookies={"access_token": "invalid.token.value"})
    assert response.status_code == 401


# ── /auth/logout ─────────────────────────────────────────────────────

def test_logout_returns_200():
    response = client.post("/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "logged out"}


def test_logout_clears_access_token_cookie():
    response = client.post("/auth/logout")
    set_cookie = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie
    # Max-Age=0 または expires が過去 → クッキー削除
    assert "max-age=0" in set_cookie.lower() or "max-age=0" in set_cookie


# ── dev-login フラグ ──────────────────────────────────────────────────

def test_dev_login_disabled_returns_403():
    with patch.object(settings, "dev_login_enabled", False):
        response = client.post("/auth/dev-login", json={"user_id": 1})
    assert response.status_code == 403


def test_dev_login_enabled_still_works():
    with patch.object(settings, "dev_login_enabled", True):
        response = client.post("/auth/dev-login", json={"user_id": 1})
    assert response.status_code == 200
