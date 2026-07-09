import uuid
from fastapi import APIRouter, Depends, Request

from packages.mcp.server import McpServer
from packages.mcp.sse import sse_connection, handle_message
from packages.auth.deps import get_current_user


def create_mcp_router(server: McpServer) -> APIRouter:
    router = APIRouter(prefix="/mcp", tags=["MCP"])

    @router.get("/sse")
    async def sse(request: Request, user: dict = Depends(get_current_user)):
        session_id = str(uuid.uuid4())
        return await sse_connection(session_id, server, user=user)

    @router.post("/message")
    async def message(session_id: str, request: Request, user: dict = Depends(get_current_user)):
        body = await request.json()
        return await handle_message(session_id, body, server, user=user)

    return router
