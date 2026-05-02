"""
Decision hypothesis generation from selected signals.
POST /signals/hypothesize → { intent, if_condition, then_adjustment, because_reason }

Uses OpenAI when available; falls back to rule-based output otherwise.
"""
import json
import logging

from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["signals"])


class SignalInput(BaseModel):
    id: str
    source_type: str = "analysis"
    content: str
    tags: list[str] = []
    score: float | None = None


class HypothesizeRequest(BaseModel):
    channel_id: int
    signals: list[SignalInput]


class HypothesizeResponse(BaseModel):
    intent: str
    if_condition: str
    then_adjustment: str
    because_reason: str


_SYSTEM_PROMPT = """\
You are a Decision Operation assistant for a decision flow management system.
Given signals from a conversation channel, generate a structured decision hypothesis.
Output ONLY valid JSON with exactly these four keys: intent, if_condition, then_adjustment, because_reason.

Rules:
- intent: one sentence stating what decision is at stake
- if_condition: completes "IF ..." — 1 sentence, observable condition from signals
- then_adjustment: completes "THEN ..." — 1 sentence, specific change to decision logic
- because_reason: completes "BECAUSE ..." — 1 sentence, grounded in signal evidence
- No other keys. No prose outside JSON.
- Respond in the same language as the input signals (Japanese if signals are in Japanese).
"""


def _fallback_hypothesis(signals: list[SignalInput]) -> HypothesizeResponse:
    contents = [s.content for s in signals[:3]]
    tags = list({tag for s in signals for tag in s.tags})[:3]
    tag_str = f"（{', '.join(tags)}）" if tags else ""
    first = contents[0] if contents else "観測されたシグナル"
    return HypothesizeResponse(
        intent=f"現在の判断フローの見直しが必要です{tag_str}",
        if_condition=f"「{first}」のようなケースが継続的に観測される場合",
        then_adjustment="該当ケースを捕捉する境界条件またはノードを追加・調整する",
        because_reason=(
            f"{len(signals)}件のシグナルが現在のフローで適切に処理されていない可能性があるため"
        ),
    )


@router.post("/signals/hypothesize", response_model=HypothesizeResponse)
async def hypothesize(req: HypothesizeRequest) -> HypothesizeResponse:
    if not req.signals:
        raise HTTPException(status_code=400, detail="signals must not be empty")

    signal_lines = "\n".join(
        f"- [{s.source_type}] {s.content}"
        + (f" (tags: {', '.join(s.tags)})" if s.tags else "")
        + (f" (score: {s.score})" if s.score is not None else "")
        for s in req.signals
    )

    if not settings.openai_api_key:
        logger.info("OpenAI key not set — using fallback hypothesis")
        return _fallback_hypothesis(req.signals)

    user_prompt = (
        f"Channel ID: {req.channel_id}\n\nSignals:\n{signal_lines}\n\n"
        "Generate the hypothesis JSON."
    )

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
            max_tokens=400,
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        return HypothesizeResponse(
            intent=str(data.get("intent", "")),
            if_condition=str(data.get("if_condition", "")),
            then_adjustment=str(data.get("then_adjustment", "")),
            because_reason=str(data.get("because_reason", "")),
        )
    except Exception as exc:
        logger.warning("Hypothesis LLM call failed, using fallback: %s", exc)
        return _fallback_hypothesis(req.signals)
