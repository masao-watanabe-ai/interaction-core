"""
RQ job: run channel analysis (rule-based + optional LLM) and publish
analysis.completed via Redis Pub/Sub.

Pipeline:
  1. Rule-based analysis
  2. LLM channel summary / insights (optional)
  3. Persist LLM results
  4. Publish analysis.completed event
  5. LLM per-user quality scoring (optional, fallback to zeros)
  6. Recalculate workspace scores with quality boost

Entry point: run_analysis_job(channel_id)
"""
import asyncio
import json
import logging
from collections import defaultdict

import redis.asyncio as aioredis
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.analysis import ChannelAnalysis
from app.models.channel import Channel
from app.models.message import Message
from app.services.analysis_service import run_analysis
from app.services.llm_service import analyze_with_llm, score_user_messages
from app.services.redis_client import PUBSUB_CHANNEL
from app.services.score_service import QualityScores, recalculate_workspace_scores

logger = logging.getLogger(__name__)


def run_analysis_job(channel_id: int) -> None:
    asyncio.run(_async_run(channel_id))


async def _async_run(channel_id: int) -> None:
    # ── Step 1: Rule-based analysis + fetch message texts ────────────
    texts: list[str] = []
    async with AsyncSessionLocal() as session:
        result = await run_analysis(channel_id, session)
        if result is None:
            logger.warning("analysis_worker: channel %d not found", channel_id)
            return
        msgs_q = await session.execute(
            select(Message.content)
            .where(Message.channel_id == channel_id)
            .order_by(Message.id.desc())
            .limit(50)
        )
        texts = list(msgs_q.scalars().all())

    # ── Step 2: LLM channel summary / insights (optional) ────────────
    summary_text = result.summary_text
    insights: list[str] = []
    suggested_actions: list[str] = []

    if texts:
        llm = await analyze_with_llm(texts, {
            "total_messages": result.total_messages,
            "active_users": result.active_users,
            "positive_count": result.positive_count,
            "negative_count": result.negative_count,
            "question_count": result.question_count,
            "top_keywords": result.top_keywords,
        })
        if llm:
            summary_text = llm.summary_text
            insights = llm.insights
            suggested_actions = llm.suggested_actions
            logger.info("analysis_worker: LLM channel analysis done for channel %d", channel_id)
        else:
            logger.info("analysis_worker: using rule-based fallback for channel %d", channel_id)

    # ── Step 3: Persist LLM results ───────────────────────────────────
    async with AsyncSessionLocal() as session:
        db_result = await session.get(ChannelAnalysis, result.id)
        if db_result is None:
            return
        db_result.summary_text = summary_text
        db_result.insights = insights
        db_result.suggested_actions = suggested_actions
        await session.commit()
        await session.refresh(db_result)

    # ── Step 4: Publish analysis.completed ───────────────────────────
    event = {
        "type": "analysis.completed",
        "payload": {
            "channel_id": db_result.channel_id,
            "result": {
                "channel_id": db_result.channel_id,
                "total_messages": db_result.total_messages,
                "top_keywords": db_result.top_keywords,
                "positive_count": db_result.positive_count,
                "negative_count": db_result.negative_count,
                "question_count": db_result.question_count,
                "active_users": db_result.active_users,
                "summary_text": db_result.summary_text,
                "insights": db_result.insights,
                "suggested_actions": db_result.suggested_actions,
                "analyzed_at": db_result.analyzed_at.isoformat(),
            },
        },
    }

    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await r.publish(PUBSUB_CHANNEL, json.dumps(event))
        logger.info("analysis_worker: published analysis.completed for channel %d", channel_id)
    except Exception as exc:
        logger.warning("analysis_worker: failed to publish event: %s", exc)
    finally:
        await r.aclose()

    # ── Step 5: LLM per-user quality scoring ─────────────────────────
    # Fetch per-user messages for this channel (used for quality eval)
    user_messages: dict[int, list[str]] = defaultdict(list)
    async with AsyncSessionLocal() as session:
        umsgs_q = await session.execute(
            select(Message.user_id, Message.content)
            .where(Message.channel_id == channel_id)
            .order_by(Message.id.desc())
            .limit(100)
        )
        for uid, content in umsgs_q.all():
            msgs = user_messages[uid]
            if len(msgs) < 5:
                msgs.append(content)

    quality_scores: dict[int, QualityScores] | None = None
    if user_messages:
        llm_quality = await score_user_messages(
            dict(user_messages),
            {
                "top_keywords": db_result.top_keywords,
                "summary_text": db_result.summary_text,
            },
        )
        if llm_quality:
            quality_scores = {
                uid: QualityScores(
                    insight_quality=qs.insight_quality,
                    discussion_impact=qs.discussion_impact,
                    decision_contribution=qs.decision_contribution,
                )
                for uid, qs in llm_quality.items()
            }
            logger.info(
                "analysis_worker: quality scoring done for %d users in channel %d",
                len(quality_scores),
                channel_id,
            )
        else:
            logger.info(
                "analysis_worker: quality scoring skipped/failed for channel %d (fallback)",
                channel_id,
            )

    # ── Step 6: Recalculate workspace scores with quality boost ───────
    async with AsyncSessionLocal() as session:
        channel = await session.get(Channel, channel_id)
        if channel:
            try:
                await recalculate_workspace_scores(
                    channel.workspace_id, session, quality_scores=quality_scores
                )
                logger.info(
                    "analysis_worker: recalculated scores for workspace %d",
                    channel.workspace_id,
                )
            except Exception as exc:
                logger.warning("analysis_worker: score recalculation failed: %s", exc)
