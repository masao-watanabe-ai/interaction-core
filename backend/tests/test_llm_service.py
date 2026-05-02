"""
Unit tests for llm_service.analyze_with_llm().

All OpenAI calls are mocked — no real API key required.
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm_service import analyze_with_llm, LLMAnalysisResult

_RULE_METRICS = {
    "total_messages": 10,
    "active_users": 3,
    "positive_count": 4,
    "negative_count": 1,
    "question_count": 2,
    "top_keywords": ["テスト", "バグ"],
}
_TEXTS = ["テストメッセージです", "バグを修正しました", "ありがとうございます"]


# ── API キー未設定 ────────────────────────────────────────────────────────────


def test_returns_none_when_no_api_key():
    with patch("app.services.llm_service.settings") as mock_cfg:
        mock_cfg.openai_api_key = ""
        result = asyncio.run(analyze_with_llm(_TEXTS, _RULE_METRICS))
    assert result is None


# ── 正常系 ────────────────────────────────────────────────────────────────────


def _mock_openai_response(payload: dict) -> MagicMock:
    msg = MagicMock()
    msg.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


def test_returns_llm_result_on_success():
    payload = {
        "summary_text": "テスト会話のサマリー",
        "insights": ["ポイント1", "ポイント2"],
        "suggested_actions": ["アクション1"],
    }

    mock_create = AsyncMock(return_value=_mock_openai_response(payload))

    with patch("app.services.llm_service.settings") as mock_cfg:
        mock_cfg.openai_api_key = "sk-test"
        mock_cfg.openai_model = "gpt-4o-mini"
        with patch("app.services.llm_service.AsyncOpenAI") as MockClient:
            mock_client = MagicMock()
            mock_client.chat.completions.create = mock_create
            MockClient.return_value = mock_client
            result = asyncio.run(analyze_with_llm(_TEXTS, _RULE_METRICS))

    assert result is not None
    assert isinstance(result, LLMAnalysisResult)
    assert result.summary_text == "テスト会話のサマリー"
    assert result.insights == ["ポイント1", "ポイント2"]
    assert result.suggested_actions == ["アクション1"]


def test_passes_rule_metrics_in_prompt():
    """Rule metrics should appear in the user prompt sent to OpenAI."""
    captured_calls: list[dict] = []

    async def capture_create(**kwargs):
        captured_calls.append(kwargs)
        return _mock_openai_response({
            "summary_text": "ok", "insights": [], "suggested_actions": []
        })

    with patch("app.services.llm_service.settings") as mock_cfg:
        mock_cfg.openai_api_key = "sk-test"
        mock_cfg.openai_model = "gpt-4o-mini"
        with patch("app.services.llm_service.AsyncOpenAI") as MockClient:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=capture_create)
            MockClient.return_value = mock_client
            asyncio.run(analyze_with_llm(_TEXTS, _RULE_METRICS))

    assert len(captured_calls) == 1
    user_content = captured_calls[0]["messages"][1]["content"]
    assert "10" in user_content         # total_messages
    assert "テスト" in user_content     # top_keywords


def test_limits_to_50_messages():
    """Only the first 50 messages should be sent to the LLM."""
    large_texts = [f"msg {i}" for i in range(200)]
    captured_calls: list[dict] = []

    async def capture_create(**kwargs):
        captured_calls.append(kwargs)
        return _mock_openai_response({
            "summary_text": "ok", "insights": [], "suggested_actions": []
        })

    with patch("app.services.llm_service.settings") as mock_cfg:
        mock_cfg.openai_api_key = "sk-test"
        mock_cfg.openai_model = "gpt-4o-mini"
        with patch("app.services.llm_service.AsyncOpenAI") as MockClient:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=capture_create)
            MockClient.return_value = mock_client
            asyncio.run(analyze_with_llm(large_texts, {}))

    user_content = captured_calls[0]["messages"][1]["content"]
    assert "最新50件" in user_content
    assert "msg 49" in user_content
    assert "msg 50" not in user_content


# ── エラー系 ──────────────────────────────────────────────────────────────────


def test_returns_none_on_api_error():
    with patch("app.services.llm_service.settings") as mock_cfg:
        mock_cfg.openai_api_key = "sk-test"
        mock_cfg.openai_model = "gpt-4o-mini"
        with patch("app.services.llm_service.AsyncOpenAI") as MockClient:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("Connection error")
            )
            MockClient.return_value = mock_client
            result = asyncio.run(analyze_with_llm(_TEXTS, _RULE_METRICS))

    assert result is None


def test_returns_none_on_invalid_json():
    msg = MagicMock()
    msg.content = "invalid json {{{}"
    choice = MagicMock()
    choice.message = msg
    bad_response = MagicMock()
    bad_response.choices = [choice]

    with patch("app.services.llm_service.settings") as mock_cfg:
        mock_cfg.openai_api_key = "sk-test"
        mock_cfg.openai_model = "gpt-4o-mini"
        with patch("app.services.llm_service.AsyncOpenAI") as MockClient:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=bad_response)
            MockClient.return_value = mock_client
            result = asyncio.run(analyze_with_llm(_TEXTS, _RULE_METRICS))

    assert result is None


def test_handles_missing_fields_gracefully():
    """LLM response missing some fields should use empty defaults."""
    payload = {"summary_text": "部分的なレスポンス"}  # no insights/suggested_actions

    with patch("app.services.llm_service.settings") as mock_cfg:
        mock_cfg.openai_api_key = "sk-test"
        mock_cfg.openai_model = "gpt-4o-mini"
        with patch("app.services.llm_service.AsyncOpenAI") as MockClient:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(
                return_value=_mock_openai_response(payload)
            )
            MockClient.return_value = mock_client
            result = asyncio.run(analyze_with_llm(_TEXTS, _RULE_METRICS))

    assert result is not None
    assert result.summary_text == "部分的なレスポンス"
    assert result.insights == []
    assert result.suggested_actions == []
