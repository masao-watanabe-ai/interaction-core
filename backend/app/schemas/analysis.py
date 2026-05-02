from datetime import datetime
from pydantic import BaseModel


class AnalysisSummary(BaseModel):
    channel_id: int
    total_messages: int
    top_keywords: list[str]
    positive_count: int
    negative_count: int
    question_count: int
    active_users: int
    summary_text: str
    insights: list[str] = []
    suggested_actions: list[str] = []
    analyzed_at: datetime

    model_config = {"from_attributes": True}


class AnalysisQueued(BaseModel):
    status: str
