from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.user_score import UserScore
from app.services.score_service import compute_impact_score

router = APIRouter(prefix="/scores", tags=["scores"])


class RankingEntry(BaseModel):
    user_id: int
    display_name: str
    points: int
    level: str
    rank: int
    enthusiasm_score: float
    insight_quality_score: float
    discussion_impact_score: float
    decision_contribution_score: float
    impact_score: float  # 0–100: normalized total quality contribution


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/ranking", response_model=list[RankingEntry])
async def get_ranking(
    workspace_id: int = 1,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(UserScore, User.display_name)
        .join(User, UserScore.user_id == User.id)
        .where(UserScore.workspace_id == workspace_id)
        .order_by(UserScore.rank.asc())
    )
    rows = result.all()
    return [
        RankingEntry(
            user_id=score.user_id,
            display_name=display_name,
            points=score.points,
            level=score.level,
            rank=score.rank,
            enthusiasm_score=score.enthusiasm_score,
            insight_quality_score=score.insight_quality_score,
            discussion_impact_score=score.discussion_impact_score,
            decision_contribution_score=score.decision_contribution_score,
            impact_score=compute_impact_score(
                score.insight_quality_score,
                score.discussion_impact_score,
                score.decision_contribution_score,
            ),
        )
        for score, display_name in rows
    ]
