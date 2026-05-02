from datetime import datetime
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.dependencies import get_current_user
from app.models.execution_event import ExecutionEvent
from app.models.decision import Decision
from app.models.user import User

router = APIRouter(prefix="/executions", tags=["executions"])


# ── Pydantic schemas ─────────────────────────────────────────────────

class ExecutionCreate(BaseModel):
    decision_id: int
    execution_type: str
    request_payload: Optional[dict[str, Any]] = None


class ExecutionStatusUpdate(BaseModel):
    status: str  # running | success | failed
    response_payload: Optional[dict[str, Any]] = None


class ExecutionResponse(BaseModel):
    id: int
    decision_id: int
    execution_type: str
    status: str
    request_payload: Optional[dict[str, Any]]
    response_payload: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


VALID_STATUSES = {"pending", "running", "success", "failed"}


# ── Routes ──────────────────────────────────────────────────────────

@router.post("", status_code=201, response_model=ExecutionResponse)
async def request_execution(
    body: ExecutionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """外部API実行のリクエストを ExecutionEvent として登録する

    Decision が approved 状態である場合のみ実行リクエストを受け付ける。

    TODO: 登録後に WS event "execution.requested" を publish する
    TODO: Orchestrator との接続で実際の実行処理を起動する
    """
    decision = await session.get(Decision, body.decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")
    if decision.status != "approved":
        raise HTTPException(
            status_code=422,
            detail=f"cannot execute: decision status is '{decision.status}'. "
                   "must be 'approved'.",
        )

    event = ExecutionEvent(
        decision_id=body.decision_id,
        execution_type=body.execution_type,
        status="pending",
        request_payload=body.request_payload,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


@router.get("", response_model=list[ExecutionResponse])
async def list_executions(
    decision_id: Optional[int] = None,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """ExecutionEvent 一覧 (実行履歴)

    Execute Chat の実行履歴パネルで使用する。
    """
    stmt = select(ExecutionEvent)
    if decision_id is not None:
        stmt = stmt.where(ExecutionEvent.decision_id == decision_id)
    if status is not None:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"invalid status: {status}")
        stmt = stmt.where(ExecutionEvent.status == status)
    stmt = stmt.order_by(ExecutionEvent.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: int,
    session: AsyncSession = Depends(get_session),
):
    event = await session.get(ExecutionEvent, execution_id)
    if event is None:
        raise HTTPException(status_code=404, detail="execution not found")
    return event


@router.patch("/{execution_id}/status", response_model=ExecutionResponse)
async def update_execution_status(
    execution_id: int,
    body: ExecutionStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """実行結果の記録 (Orchestrator からのコールバック用)

    TODO: 更新後に WS event "execution.completed" を publish する
    """
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"invalid status: {body.status}")
    event = await session.get(ExecutionEvent, execution_id)
    if event is None:
        raise HTTPException(status_code=404, detail="execution not found")

    event.status = body.status
    if body.response_payload is not None:
        event.response_payload = body.response_payload

    await session.commit()
    await session.refresh(event)
    return event
