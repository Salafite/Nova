import asyncio
from fastapi import FastAPI

from packages.mcp.server import McpServer
from packages.mcp.router import create_mcp_router
from packages.mcp.sse import _sessions, handle_message
from packages.mcp.types import Tool
from packages.mcp.registry import register_tool
from packages.auth.deps import get_current_user


class TestSseTransport:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()
        registry._resources.clear()
        registry._prompts.clear()
        _sessions.clear()
        self.server = McpServer(name="TestSSE", version="1.0")
        self.app = FastAPI()
        self.app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "test", "role": "admin"}
        self.app.include_router(create_mcp_router(self.server))

    def test_sse_route_is_registered(self):
        paths = []
        for r in self.app.routes:
            if hasattr(r, 'path'):
                paths.append(r.path)
            elif hasattr(r, 'original_router'):
                for sr in r.original_router.routes:
                    if hasattr(sr, 'path'):
                        paths.append(sr.path)
        assert "/mcp/sse" in paths
        assert "/mcp/message" in paths

    def test_message_post_via_testclient(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.post("/mcp/message?session_id=nonexistent", json={
            "jsonrpc": "2.0", "id": 1, "method": "ping",
        }, headers={"Authorization": "Bearer test"})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_handle_message_puts_response_on_queue(self):
        sid = "queue-test"
        _sessions[sid] = {"queue": asyncio.Queue(), "user": None}
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(handle_message(sid, {
                "jsonrpc": "2.0", "id": 1, "method": "ping",
            }, self.server))
            resp = loop.run_until_complete(_sessions[sid]["queue"].get())
            assert resp["id"] == 1
            assert resp["result"] == {}
        finally:
            loop.close()
            _sessions.pop(sid, None)

    def test_handle_message_tool_call_response(self):
        register_tool(
            Tool(name="hello", description="Says hello", input_schema={
                "type": "object", "properties": {"name": {"type": "string"}},
            }),
            lambda name: f"Hello, {name}!",
        )
        sid = "tool-test"
        _sessions[sid] = {"queue": asyncio.Queue(), "user": None}
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(handle_message(sid, {
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": "hello", "arguments": {"name": "Nova"}},
            }, self.server))
            resp = loop.run_until_complete(_sessions[sid]["queue"].get())
            assert "Hello, Nova!" in resp["result"]["content"][0]["text"]
        finally:
            loop.close()
            _sessions.pop(sid, None)

    def test_handle_message_notification_skips_queue(self):
        sid = "notif-test"
        _sessions[sid] = {"queue": asyncio.Queue(), "user": None}
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(handle_message(sid, {
                "jsonrpc": "2.0", "method": "notifications/initialized",
            }, self.server))
            assert _sessions[sid]["queue"].empty()
        finally:
            loop.close()
            _sessions.pop(sid, None)

    def test_handle_message_nonexistent_session(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(handle_message("ghost", {
                "jsonrpc": "2.0", "id": 1, "method": "ping",
            }, self.server))
            assert result == {"ok": True}
        finally:
            loop.close()

    def test_sse_generator_yields_endpoint_event(self):
        from packages.mcp.sse import sse_connection
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(sse_connection("gen-sid-1", self.server))
            gen = response.body_iterator
            event = loop.run_until_complete(gen.__anext__())
            assert "event: endpoint" in event
            assert "/mcp/message?session_id=gen-sid-1" in event
            gen.aclose()
        finally:
            loop.close()
            _sessions.pop("gen-sid-1", None)

    def test_sse_generator_yields_message_after_queue_put(self):
        from packages.mcp.sse import sse_connection
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            sid = "msg-gen-test"
            response = loop.run_until_complete(sse_connection(sid, self.server))
            gen = response.body_iterator

            event1 = loop.run_until_complete(gen.__anext__())
            assert "event: endpoint" in event1

            _sessions[sid]["queue"].put_nowait({"jsonrpc": "2.0", "id": 1, "result": {}})
            event2 = loop.run_until_complete(gen.__anext__())
            assert "event: message" in event2
            assert "jsonrpc" in event2
            gen.aclose()
        finally:
            loop.close()
            _sessions.pop(sid, None)
