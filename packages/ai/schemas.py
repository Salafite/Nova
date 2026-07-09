from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str | None = None
    tool_calls: list | None = None
    tool_call_id: str | None = None


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatEvent(BaseModel):
    type: str
    content: str | None = None
    name: str | None = None
