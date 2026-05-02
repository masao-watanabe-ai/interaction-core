from datetime import datetime
from typing import Optional
from sqlalchemy import Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Decision(Base):
    """Decision: AI Signalから昇格した意思決定候補を管理するモデル

    Signal ≠ Decision の原則に基づき、AIが出力した Signal (分析結果) を
    人間が明示的に Decision に変換することで追跡可能な意思決定候補となる。

    Status フロー:
        proposed → reviewing → approved / rejected → executed
    """
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), nullable=False)
    source_message_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("messages.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # proposed | reviewing | approved | rejected | executed
    status: Mapped[str] = mapped_column(Text, nullable=False, default="proposed")
    owner_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
