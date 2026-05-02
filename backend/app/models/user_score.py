from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Float, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class UserScore(Base):
    __tablename__ = "user_scores"
    __table_args__ = (UniqueConstraint("user_id", "workspace_id", name="uq_user_workspace_score"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reaction_received_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    positive_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    important_message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enthusiasm_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Semantic quality scores from LLM analysis (0.0–1.0 each)
    insight_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    discussion_impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    decision_contribution_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="Bronze")
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
