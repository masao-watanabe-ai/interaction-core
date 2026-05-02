from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.dependencies import get_current_user
from app.models.decision import Decision
from app.models.user import User

router = APIRouter(prefix="/decisions", tags=["decisions"])


# ── Pydantic schemas (最小スキーマ) ─────────────────────────────────

class DecisionCreate(BaseModel):
    channel_id: int
    title: str
    description: Optional[str] = None
    source_message_id: Optional[int] = None
    owner_user_id: Optional[int] = None


class DecisionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    owner_user_id: Optional[int] = None


class DecisionResponse(BaseModel):
    id: int
    channel_id: int
    source_message_id: Optional[int]
    title: str
    description: Optional[str]
    status: str
    owner_user_id: Optional[int]
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


VALID_STATUSES = {"proposed", "reviewing", "approved", "rejected", "executed"}


# ── Routes ──────────────────────────────────────────────────────────

@router.post("", status_code=201, response_model=DecisionResponse)
async def create_decision(
    body: DecisionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """AI Signal → Decision への変換エントリポイント

    TODO: Decision 作成後に WS event "decision.created" を publish する
    """
    decision = Decision(
        channel_id=body.channel_id,
        source_message_id=body.source_message_id,
        title=body.title,
        description=body.description,
        status="proposed",
        owner_user_id=body.owner_user_id,
        created_by=current_user.id,
    )
    session.add(decision)
    await session.commit()
    await session.refresh(decision)
    return decision


@router.get("", response_model=list[DecisionResponse])
async def list_decisions(
    channel_id: Optional[int] = None,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """Decision 一覧取得

    Human Gate Chat で承認待ち Decision を表示するために使用する。
    例: GET /decisions?channel_id=1&status=proposed
    """
    stmt = select(Decision)
    if channel_id is not None:
        stmt = stmt.where(Decision.channel_id == channel_id)
    if status is not None:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"invalid status: {status}")
        stmt = stmt.where(Decision.status == status)
    stmt = stmt.order_by(Decision.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    decision_id: int,
    session: AsyncSession = Depends(get_session),
):
    decision = await session.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")
    return decision


@router.patch("/{decision_id}", response_model=DecisionResponse)
async def update_decision(
    decision_id: int,
    body: DecisionUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Decision 状態更新

    TODO: 更新後に WS event "decision.updated" を publish する
    """
    decision = await session.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")
    if body.status is not None and body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"invalid status: {body.status}")
    if body.title is not None:
        decision.title = body.title
    if body.description is not None:
        decision.description = body.description
    if body.status is not None:
        decision.status = body.status
    if body.owner_user_id is not None:
        decision.owner_user_id = body.owner_user_id
    await session.commit()
    await session.refresh(decision)
    return decision
