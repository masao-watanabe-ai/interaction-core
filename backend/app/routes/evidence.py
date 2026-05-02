import logging
import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.dependencies import get_current_user
from app.models.evidence import EvidenceItem
from app.models.user import User
from app.services.websocket_service import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evidence", tags=["evidence"])

UPLOAD_DIR = "/uploads"


class EvidenceResponse(BaseModel):
    id: int
    channel_id: int
    uploaded_by: int
    file_name: str
    file_path: str
    mime_type: str
    extracted_text: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/upload", status_code=201, response_model=EvidenceResponse)
async def upload_evidence(
    channel_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    stored_name = f"{uuid.uuid4()}{ext}"
    stored_path = os.path.join(UPLOAD_DIR, stored_name)

    contents = await file.read()
    with open(stored_path, "wb") as f:
        f.write(contents)

    item = EvidenceItem(
        channel_id=channel_id,
        uploaded_by=current_user.id,
        file_name=file.filename or stored_name,
        file_path=stored_path,
        mime_type=file.content_type or "application/octet-stream",
        extracted_text=None,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)

    # Redis が落ちていても upload は成功済み — broadcast 失敗は握り潰す
    try:
        await manager.broadcast({
            "type": "evidence.created",
            "payload": {
                "id": item.id,
                "channel_id": item.channel_id,
                "uploaded_by": item.uploaded_by,
                "file_name": item.file_name,
                "file_path": item.file_path,
                "mime_type": item.mime_type,
                "extracted_text": item.extracted_text,
                "created_at": item.created_at.isoformat(),
            },
        })
    except Exception as e:
        logger.warning("evidence.created broadcast failed: %s", e)

    return item


@router.get("", response_model=list[EvidenceResponse])
async def list_evidence(
    channel_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(EvidenceItem)
    if channel_id is not None:
        stmt = stmt.where(EvidenceItem.channel_id == channel_id)
    stmt = stmt.order_by(EvidenceItem.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()
