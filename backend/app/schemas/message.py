from datetime import datetime
from pydantic import BaseModel, field_validator


class MessageCreate(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("content must not be empty")
        if len(v) > 2000:
            raise ValueError("content must be at most 2000 characters")
        return v


class MessageResponse(BaseModel):
    id: int
    channel_id: int
    user_id: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
