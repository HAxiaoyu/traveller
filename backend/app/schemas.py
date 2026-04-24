from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str = Field(default="新规划", max_length=200)


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionDetail(SessionResponse):
    messages: list = []
    slots: dict = {}
    travel_plan: Optional[dict] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    model_provider: str = Field(default="openai")
    model_name: str = Field(default="gpt-4o")
    api_key: str = Field(default="")


class ChatEvent(BaseModel):
    type: str  # status | plan_chunk | done | error
    content: str = ""
    data: Optional[dict] = None
