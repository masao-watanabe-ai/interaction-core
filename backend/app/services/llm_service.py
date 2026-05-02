"""
LLM-based channel analysis using OpenAI.

analyze_with_llm() returns None when:
  - OPENAI_API_KEY is not set
  - OpenAI API call fails for any reason

Callers must always implement a rule-based fallback.
"""
import json
import logging
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
あなたはチャットチャンネルの会話を分析するAIアシスタントです。
与えられたメッセージと統計情報を元に以下を日本語で作成し、必ずJSON形式で返答してください。

出力フォーマット（必ずこの形式で）:
{
  "summary_text": "会話全体を2〜3文で要約した文章",
  "insights": ["重要な論点や気づき（最大3つ）"],
  "suggested_actions": ["次に取るべき具体的なアクション（最大3つ）"]
}
"""


@dataclass
class LLMAnalysisResult:
    summary_text: str
    insights: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)


@dataclass
class UserQualityScores:
    """Per-user semantic quality scores derived from LLM analysis (0.0–1.0 each)."""
    insight_quality: float = 0.0
    discussion_impact: float = 0.0
    decision_contribution: float = 0.0


async def analyze_with_llm(
    texts: list[str],
    rule_metrics: dict,
) -> LLMAnalysisResult | None:
    """
    Call OpenAI to generate a natural-language analysis.
    Returns None if the API key is unset or the call fails.
    """
    if not settings.openai_api_key:
        return None

    sample = texts[:50]
    messages_block = "\n".join(f"- {t}" for t in sample) or "（メッセージなし）"

    user_prompt = f"""\
以下のチャット会話を分析してください。

【メッセージ一覧（最新{len(sample)}件）】
{messages_block}

【統計情報】
- 総メッセージ数: {rule_metrics.get('total_messages', 0)}
- 参加ユーザー数: {rule_metrics.get('active_users', 0)}
- ポジティブ: {rule_metrics.get('positive_count', 0)} / ネガティブ: {rule_metrics.get('negative_count', 0)} / 質問: {rule_metrics.get('question_count', 0)}
- 頻出キーワード: {', '.join(rule_metrics.get('top_keywords', [])[:5]) or 'なし'}
"""

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=800,
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        return LLMAnalysisResult(
            summary_text=str(data.get("summary_text", "")),
            insights=[str(x) for x in data.get("insights", [])],
            suggested_actions=[str(x) for x in data.get("suggested_actions", [])],
        )
    except Exception as exc:
        logger.warning("LLM analysis failed, falling back to rule-based: %s", exc)
        return None


_QUALITY_SYSTEM_PROMPT = """\
あなたはチャット会話を分析し、各参加者の発言の「質」を評価するAIです。
必ずJSON形式のみで返答し、それ以外のテキストは含めないでください。
"""


async def score_user_messages(
    user_messages: dict[int, list[str]],
    channel_context: dict,
) -> dict[int, UserQualityScores] | None:
    """
    Use LLM to evaluate each user's contribution quality within a channel discussion.

    Returns a dict of user_id → UserQualityScores, or None when the API key is
    unset or the call fails. Callers must fall back to zero scores on None.
    """
    if not settings.openai_api_key or not user_messages:
        return None

    # Limit to 10 most active users, 5 messages each, to keep prompt size bounded
    top_users = sorted(user_messages.items(), key=lambda x: -len(x[1]))[:10]
    lines: list[str] = []
    for uid, msgs in top_users:
        for msg in msgs[:5]:
            safe = msg.replace('"', "'")
            lines.append(f'[user:{uid}] "{safe}"')

    if not lines:
        return None

    keywords = ", ".join(str(k) for k in channel_context.get("top_keywords", [])[:5]) or "なし"
    summary = channel_context.get("summary_text", "") or "（要約なし）"

    user_prompt = f"""\
チャンネルの文脈:
キーワード: {keywords}
概要: {summary}

各ユーザーの発言:
{chr(10).join(lines)}

各 user_id に対して以下の3指標を 0.0〜1.0 で評価してください。
- insight_quality    : 洞察力・知見の深さ（薄い=0, 深い=1）
- discussion_impact  : 議論を活性化した度合い（受動的=0, 主導的=1）
- decision_contribution: 意思決定に貢献した度合い（なし=0, 中核的=1）

出力フォーマット（このJSONのみ）:
{{"users": [{{"user_id": <id>, "insight_quality": <0-1>, "discussion_impact": <0-1>, "decision_contribution": <0-1>}}]}}
"""

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _QUALITY_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=512,
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)

        def _clamp(v: object) -> float:
            return max(0.0, min(1.0, float(v)))  # type: ignore[arg-type]

        result: dict[int, UserQualityScores] = {}
        for entry in data.get("users", []):
            uid = int(entry.get("user_id", 0))
            if uid <= 0:
                continue
            result[uid] = UserQualityScores(
                insight_quality=_clamp(entry.get("insight_quality", 0.0)),
                discussion_impact=_clamp(entry.get("discussion_impact", 0.0)),
                decision_contribution=_clamp(entry.get("decision_contribution", 0.0)),
            )
        return result or None
    except Exception as exc:
        logger.warning("LLM quality scoring failed: %s", exc)
        return None
