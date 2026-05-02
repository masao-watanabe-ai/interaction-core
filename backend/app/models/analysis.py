from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import Text, DateTime, ForeignKey, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ChannelAnalysis(Base):
    __tablename__ = "channel_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id"), nullable=False, index=True
    )
    total_messages: Mapped[int] = mapped_column(Integer, nullable=False)
    positive_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    top_keywords: Mapped[list] = mapped_column(JSON, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    insights: Mapped[list] = mapped_column(JSON, nullable=False, server_default=sa.text("'[]'"))
    suggested_actions: Mapped[list] = mapped_column(JSON, nullable=False, server_default=sa.text("'[]'"))
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
