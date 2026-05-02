from datetime import datetime
from typing import Optional
from sqlalchemy import Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class HumanAction(Base):
    """HumanAction: 人間が Decision に対して行う操作を記録するモデル

    Human Gate Chat で利用する。AIの出力はSignalであり、
    ここに記録されるのは人間が下した明示的な判断のみ。

    action_type: approve / reject / revise / hold / escalate
    """
    __tablename__ = "human_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # approve | reject | revise | hold | escalate
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
