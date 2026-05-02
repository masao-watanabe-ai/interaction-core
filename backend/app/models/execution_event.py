from datetime import datetime
from typing import Optional
from sqlalchemy import Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ExecutionEvent(Base):
    """ExecutionEvent: Decision を受けて実行される外部API操作の記録

    Execute Chat で利用する。Decision が approved になった後に
    Orchestrator がトリガーし、実行ログとして蓄積される。

    status: pending | running | success | failed
    """
    __tablename__ = "execution_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id"), nullable=False)
    execution_type: Mapped[str] = mapped_column(Text, nullable=False)
    # pending | running | success | failed
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    request_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    response_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
