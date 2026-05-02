"""
User Score & Ranking calculation.

Scoring is split into two layers:
  1. Rule-based  – activity counts (centralized in WEIGHTS)
  2. Quality-based – LLM-derived semantic scores (centralized in QUALITY_WEIGHTS)

points = rule_points
       + insight_quality_score      * QUALITY_WEIGHTS["insight_quality_score"]
       + discussion_impact_score    * QUALITY_WEIGHTS["discussion_impact_score"]
       + decision_contribution_score * QUALITY_WEIGHTS["decision_contribution_score"]

Change WEIGHTS / QUALITY_WEIGHTS to retune without touching logic.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.models.message import Message
from app.models.user_score import UserScore
from app.module.analysis.emotion import classify_message

# ── Activity weights ──────────────────────────────────────────────────
WEIGHTS = {
    "message_count": 2,
    "reply_count": 3,
    "reaction_received_count": 5,
    "question_count": 2,
    "positive_count": 3,
    "important_message_count": 10,
}

# ── Semantic quality weights ──────────────────────────────────────────
QUALITY_WEIGHTS = {
    "insight_quality_score": 10,
    "discussion_impact_score": 5,
    "decision_contribution_score": 20,
}

_MAX_QUALITY_PTS: float = sum(QUALITY_WEIGHTS.values())  # 35


class QualityScores(TypedDict):
    insight_quality: float
    discussion_impact: float
    decision_contribution: float


# ── Core computation ──────────────────────────────────────────────────

def compute_points(
    *,
    message_count: int,
    reply_count: int,
    reaction_received_count: int,
    question_count: int,
    positive_count: int,
    important_message_count: int,
    insight_quality_score: float = 0.0,
    discussion_impact_score: float = 0.0,
    decision_contribution_score: float = 0.0,
) -> int:
    rule_pts = (
        message_count * WEIGHTS["message_count"]
        + reply_count * WEIGHTS["reply_count"]
        + reaction_received_count * WEIGHTS["reaction_received_count"]
        + question_count * WEIGHTS["question_count"]
        + positive_count * WEIGHTS["positive_count"]
        + important_message_count * WEIGHTS["important_message_count"]
    )
    quality_pts = (
        insight_quality_score * QUALITY_WEIGHTS["insight_quality_score"]
        + discussion_impact_score * QUALITY_WEIGHTS["discussion_impact_score"]
        + decision_contribution_score * QUALITY_WEIGHTS["decision_contribution_score"]
    )
    return int(rule_pts + quality_pts)


def compute_level(points: int) -> str:
    if points >= 1000:
        return "Platinum"
    if points >= 500:
        return "Gold"
    if points >= 200:
        return "Silver"
    return "Bronze"


def normalize_enthusiasm(points: int, max_points: int) -> float:
    if max_points <= 0:
        return 0.0
    return round(min(100.0, (points / max_points) * 100), 1)


def compute_impact_score(
    insight_quality_score: float,
    discussion_impact_score: float,
    decision_contribution_score: float,
) -> float:
    """Normalize total quality contribution to 0–100."""
    if _MAX_QUALITY_PTS <= 0:
        return 0.0
    raw = (
        insight_quality_score * QUALITY_WEIGHTS["insight_quality_score"]
        + discussion_impact_score * QUALITY_WEIGHTS["discussion_impact_score"]
        + decision_contribution_score * QUALITY_WEIGHTS["decision_contribution_score"]
    )
    return round(min(100.0, (raw / _MAX_QUALITY_PTS) * 100), 1)


def _is_reply(content: str) -> bool:
    return content.startswith("@")


def _is_important(content: str) -> bool:
    return "!" in content or "！" in content


# ── Workspace score recalculation ─────────────────────────────────────

async def recalculate_workspace_scores(
    workspace_id: int,
    session: AsyncSession,
    quality_scores: dict[int, QualityScores] | None = None,
) -> list[UserScore]:
    """
    Recalculate and upsert UserScore for every active user in the workspace.

    quality_scores is keyed by user_id and carries LLM-derived scores for
    users who participated in the most recently analyzed channel.  Users
    absent from quality_scores keep their previously stored quality values
    so that a single-channel analysis does not zero-out other users.

    Returns the updated list sorted by rank ascending.
    """
    # 1. Workspace channel IDs
    channels_q = await session.execute(
        select(Channel.id).where(Channel.workspace_id == workspace_id)
    )
    channel_ids = list(channels_q.scalars().all())
    if not channel_ids:
        return []

    # 2. All messages in the workspace
    msgs_q = await session.execute(
        select(Message.user_id, Message.content).where(
            Message.channel_id.in_(channel_ids)
        )
    )
    rows = msgs_q.all()
    if not rows:
        return []

    # 3. Per-user activity stats
    user_stats: dict[int, dict] = defaultdict(lambda: {
        "message_count": 0,
        "reply_count": 0,
        "reaction_received_count": 0,
        "question_count": 0,
        "positive_count": 0,
        "important_message_count": 0,
    })
    for user_id, content in rows:
        s = user_stats[user_id]
        s["message_count"] += 1
        if _is_reply(content):
            s["reply_count"] += 1
        sentiment = classify_message(content)
        if sentiment == "question":
            s["question_count"] += 1
        elif sentiment == "positive":
            s["positive_count"] += 1
        if _is_important(content):
            s["important_message_count"] += 1

    # 4. Bulk-fetch existing scores (for upsert + quality score preservation)
    existing_q = await session.execute(
        select(UserScore).where(UserScore.workspace_id == workspace_id)
    )
    existing: dict[int, UserScore] = {s.user_id: s for s in existing_q.scalars().all()}

    # 5. Resolve quality scores per user
    #    Priority: new LLM scores > existing DB scores > zero
    def _quality(uid: int) -> tuple[float, float, float]:
        if quality_scores and uid in quality_scores:
            qs = quality_scores[uid]
            return (
                float(qs.get("insight_quality", 0.0)),
                float(qs.get("discussion_impact", 0.0)),
                float(qs.get("decision_contribution", 0.0)),
            )
        prev = existing.get(uid)
        if prev is not None:
            return (
                prev.insight_quality_score,
                prev.discussion_impact_score,
                prev.decision_contribution_score,
            )
        return 0.0, 0.0, 0.0

    # 6. Compute points (includes quality boost)
    user_points: dict[int, int] = {}
    for uid, stats in user_stats.items():
        insight, discussion, decision = _quality(uid)
        user_points[uid] = compute_points(
            **stats,
            insight_quality_score=insight,
            discussion_impact_score=discussion,
            decision_contribution_score=decision,
        )

    max_pts = max(user_points.values(), default=0)
    sorted_users = sorted(user_points.items(), key=lambda x: -x[1])

    # 7. Upsert
    now = datetime.now(timezone.utc)
    scores: list[UserScore] = []

    for rank_pos, (uid, pts) in enumerate(sorted_users, start=1):
        stats = user_stats[uid]
        insight, discussion, decision = _quality(uid)
        enthusiasm = normalize_enthusiasm(pts, max_pts)
        level = compute_level(pts)

        score = existing.get(uid)
        if score is not None:
            score.message_count = stats["message_count"]
            score.reply_count = stats["reply_count"]
            score.reaction_received_count = stats["reaction_received_count"]
            score.question_count = stats["question_count"]
            score.positive_count = stats["positive_count"]
            score.important_message_count = stats["important_message_count"]
            score.insight_quality_score = insight
            score.discussion_impact_score = discussion
            score.decision_contribution_score = decision
            score.enthusiasm_score = enthusiasm
            score.points = pts
            score.level = level
            score.rank = rank_pos
            score.calculated_at = now
        else:
            score = UserScore(
                user_id=uid,
                workspace_id=workspace_id,
                message_count=stats["message_count"],
                reply_count=stats["reply_count"],
                reaction_received_count=stats["reaction_received_count"],
                question_count=stats["question_count"],
                positive_count=stats["positive_count"],
                important_message_count=stats["important_message_count"],
                insight_quality_score=insight,
                discussion_impact_score=discussion,
                decision_contribution_score=decision,
                enthusiasm_score=enthusiasm,
                points=pts,
                level=level,
                rank=rank_pos,
                calculated_at=now,
            )
            session.add(score)

        scores.append(score)

    await session.commit()
    return scores
