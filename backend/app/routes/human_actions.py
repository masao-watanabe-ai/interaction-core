from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.dependencies import get_current_user
from app.models.human_action import HumanAction
from app.models.decision import Decision
from app.models.user import User

router = APIRouter(prefix="/human_actions", tags=["human_actions"])


# ── Pydantic schemas ─────────────────────────────────────────────────

class HumanActionCreate(BaseModel):
    decision_id: int
    action_type: str  # approve | reject | revise | hold | escalate
    comment: Optional[str] = None


class HumanActionResponse(BaseModel):
    id: int
    decision_id: int
    user_id: int
    action_type: str
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


VALID_ACTION_TYPES = {"approve", "reject", "revise", "hold", "escalate"}

# action_type → Decision 遷移先 status のマッピング
ACTION_TO_STATUS: dict[str, str] = {
    "approve":   "approved",
    "reject":    "rejected",
    "revise":    "reviewing",
    "hold":      "reviewing",
    "escalate":  "reviewing",
}


# ── Routes ──────────────────────────────────────────────────────────

@router.post("", status_code=201, response_model=HumanActionResponse)
async def create_human_action(
    body: HumanActionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """人間の判断を HumanAction として記録し、Decision の status を遷移させる

    Signal ≠ Decision 原則: ここに記録されるのは人間が下した明示的な判断のみ。

    TODO: 作成後に WS event "human_action.created" を publish する
    """
    if body.action_type not in VALID_ACTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"invalid action_type: {body.action_type}. "
                   f"valid: {sorted(VALID_ACTION_TYPES)}",
        )
    decision = await session.get(Decision, body.decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")

    action = HumanAction(
        decision_id=body.decision_id,
        user_id=current_user.id,
        action_type=body.action_type,
        comment=body.comment,
    )
    session.add(action)

    # Decision status を自動遷移
    new_status = ACTION_TO_STATUS.get(body.action_type)
    if new_status:
        decision.status = new_status

    await session.commit()
    await session.refresh(action)
    return action


@router.get("", response_model=list[HumanActionResponse])
async def list_human_actions(
    decision_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    """HumanAction 一覧 (Decision の審議履歴)"""
    stmt = select(HumanAction)
    if decision_id is not None:
        stmt = stmt.where(HumanAction.decision_id == decision_id)
    stmt = stmt.order_by(HumanAction.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()
