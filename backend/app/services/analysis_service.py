from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.models.channel import Channel
from app.models.message import Message
from app.models.analysis import ChannelAnalysis
from app.module.analysis.keyword import extract_keywords
from app.module.analysis.emotion import analyze_emotions


def _build_summary(
    total: int, active: int, pos: int, neg: int, q: int, keywords: list[str]
) -> str:
    if total == 0:
        return "このチャンネルにはまだメッセージがありません。"
    parts = [f"このチャンネルには {total} 件のメッセージがあります。"]
    parts.append(f"参加ユーザーは {active} 人です。")
    if keywords:
        parts.append(f"よく使われる語: {', '.join(keywords[:5])}。")
    if pos > neg:
        parts.append("全体的にポジティブなトーンです。")
    elif neg > pos:
        parts.append("問題や課題についての議論が多いようです。")
    if q > 0:
        parts.append(f"{q} 件の質問が含まれています。")
    return "".join(parts)


async def run_analysis(channel_id: int, session: AsyncSession) -> ChannelAnalysis | None:
    if await session.get(Channel, channel_id) is None:
        return None

    result = await session.execute(
        select(Message)
        .where(Message.channel_id == channel_id)
        .order_by(Message.id.desc())
        .limit(200)
    )
    messages = result.scalars().all()

    texts = [m.content for m in messages]
    user_ids = {m.user_id for m in messages}
    keywords = extract_keywords(texts)
    emotions = analyze_emotions(texts)

    analysis = ChannelAnalysis(
        channel_id=channel_id,
        total_messages=len(messages),
        positive_count=emotions["positive_count"],
        negative_count=emotions["negative_count"],
        question_count=emotions["question_count"],
        active_users=len(user_ids),
        top_keywords=keywords,
        summary_text=_build_summary(
            len(messages), len(user_ids),
            emotions["positive_count"], emotions["negative_count"],
            emotions["question_count"], keywords,
        ),
    )
    session.add(analysis)
    await session.commit()
    await session.refresh(analysis)
    return analysis


def enqueue_analysis(channel_id: int) -> None:
    """Enqueue an analysis job on the 'analysis' RQ queue (sync — uses sync Redis)."""
    from redis import Redis as SyncRedis
    from rq import Queue
    conn = SyncRedis.from_url(settings.redis_url)
    try:
        queue = Queue("analysis", connection=conn)
        queue.enqueue("app.worker.analysis_worker.run_analysis_job", channel_id)
    finally:
        conn.close()


async def get_latest_analysis(channel_id: int, session: AsyncSession) -> ChannelAnalysis | None:
    result = await session.execute(
        select(ChannelAnalysis)
        .where(ChannelAnalysis.channel_id == channel_id)
        .order_by(ChannelAnalysis.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
