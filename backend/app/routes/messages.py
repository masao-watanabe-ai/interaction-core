from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.dependencies import get_current_user
from app.models.channel import Channel
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse
from app.services.websocket_service import manager

router = APIRouter(prefix="/channels", tags=["messages"])


async def _get_channel_or_404(channel_id: int, session: AsyncSession) -> Channel:
    result = await session.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if channel is None:
        raise HTTPException(status_code=404, detail="channel not found")
    return channel


@router.get("/{channel_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    channel_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    before_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    await _get_channel_or_404(channel_id, session)

    stmt = select(Message).where(Message.channel_id == channel_id)
    if before_id is not None:
        stmt = stmt.where(Message.id < before_id)
    stmt = stmt.order_by(Message.id.desc()).limit(limit)

    result = await session.execute(stmt)
    messages = result.scalars().all()
    return list(reversed(messages))


@router.post("/{channel_id}/messages", response_model=MessageResponse, status_code=201)
async def create_message(
    channel_id: int,
    body: MessageCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _get_channel_or_404(channel_id, session)

    message = Message(
        channel_id=channel_id,
        user_id=current_user.id,
        content=body.content,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)

    await manager.broadcast({
        "type": "message.created",
        "payload": {
            "id": message.id,
            "channel_id": message.channel_id,
            "user_id": message.user_id,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        },
    })

    return message
