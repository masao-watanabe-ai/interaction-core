from pydantic import BaseModel, field_validator


class ChannelCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        return v


class ChannelResponse(BaseModel):
    id: int
    name: str
    workspace_id: int

    model_config = {"from_attributes": True}
