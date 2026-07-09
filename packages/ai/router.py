from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from packages.ai.schemas import ChatRequest
from packages.ai.service import stream_chat
from packages.auth.deps import get_current_user

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post("/chat")
async def chat(body: ChatRequest, user: dict = Depends(get_current_user)):
    return StreamingResponse(
        stream_chat(body.history, body.message, user=user),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
