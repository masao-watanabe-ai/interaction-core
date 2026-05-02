from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database import get_session
from app.models.channel import Channel
from app.schemas.channel import ChannelCreate, ChannelResponse

router = APIRouter(prefix="/channels", tags=["channels"])

DEFAULT_WORKSPACE_ID = 1


@router.get("", response_model=list[ChannelResponse])
async def list_channels(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Channel).order_by(Channel.id))
    return result.scalars().all()


@router.post("", response_model=ChannelResponse, status_code=201)
async def create_channel(
    body: ChannelCreate,
    session: AsyncSession = Depends(get_session),
):
    channel = Channel(workspace_id=DEFAULT_WORKSPACE_ID, name=body.name)
    session.add(channel)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="channel name already exists")
    await session.refresh(channel)
    return channel
