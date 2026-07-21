import json
import asyncio
from starlette.responses import StreamingResponse

from packages.mcp.server import McpServer


_sessions: dict[str, dict] = {}


async def sse_connection(session_id: str, server: McpServer, user: dict | None = None):
    queue: asyncio.Queue = asyncio.Queue()
    _sessions[session_id] = {"queue": queue, "user": user}
    endpoint_url = f"/mcp/message?session_id={session_id}"

    async def event_generator():
        try:
            yield f"event: endpoint\ndata: {endpoint_url}\n\n"
            while True:
                message = await queue.get()
                yield f"event: message\ndata: {json.dumps(message)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            _sessions.pop(session_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def handle_message(session_id: str, raw_body: dict, server: McpServer, user: dict | None = None):
    session = _sessions.get(session_id)
    session_user = session.get("user") if session else user
    response = server.handle_request(raw_body, user=session_user)
    if response is not None and session:
        await session["queue"].put(response)
    return {"ok": True}
