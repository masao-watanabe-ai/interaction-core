import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.models.channel import Channel
from app.schemas.analysis import AnalysisSummary, AnalysisQueued
from app.services.analysis_service import enqueue_analysis, get_latest_analysis

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/channels/{channel_id}", status_code=202, response_model=AnalysisQueued)
async def analyze_channel(
    channel_id: int,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(Channel, channel_id) is None:
        raise HTTPException(status_code=404, detail="channel not found")
    try:
        await asyncio.to_thread(enqueue_analysis, channel_id)
    except Exception:
        raise HTTPException(status_code=503, detail="queue unavailable")
    return AnalysisQueued(status="queued")


@router.get("/channels/{channel_id}/summary", response_model=AnalysisSummary)
async def get_channel_summary(
    channel_id: int,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(Channel, channel_id) is None:
        raise HTTPException(status_code=404, detail="channel not found")
    analysis = await get_latest_analysis(channel_id, session)
    if analysis is None:
        raise HTTPException(status_code=404, detail="no analysis found")
    return analysis
