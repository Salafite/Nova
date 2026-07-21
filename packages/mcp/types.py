from pydantic import BaseModel
from typing import Any


class Tool(BaseModel):
    name: str
    description: str
    input_schema: dict
    tier: str = "tier1"


class Resource(BaseModel):
    uri: str
    name: str
    description: str
    mime_type: str = "application/json"


class PromptArg(BaseModel):
    name: str
    description: str
    required: bool = False


class Prompt(BaseModel):
    name: str
    description: str
    arguments: list[PromptArg] = []


class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Any = None


class UserContext(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    email: str | None = None
    role: str | None = None
    permissions: list[str] = []
    business_id: int | None = None
