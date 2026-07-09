import pytest
from packages.mcp.server import McpServer
from packages.mcp.types import Tool, Resource, Prompt
from packages.mcp.registry import register_tool, register_resource, register_prompt


class TestMcpServer:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()
        registry._resources.clear()
        registry._prompts.clear()
        self.server = McpServer(name="TestServer", version="1.0")

    def _req(self, method, params=None, req_id=1):
        msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params:
            msg["params"] = params
        return msg

    def test_initialize(self):
        resp = self.server.handle_request(self._req("initialize", {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "test", "version": "1.0"},
        }))
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert resp["result"]["serverInfo"]["name"] == "TestServer"

    def test_initialized_notification_returns_none(self):
        resp = self.server.handle_request({
            "jsonrpc": "2.0", "method": "notifications/initialized"
        })
        assert resp is None

    def test_ping(self):
        resp = self.server.handle_request(self._req("ping"))
        assert resp["result"] == {}

    def test_tools_list_empty(self):
        resp = self.server.handle_request(self._req("tools/list"))
        assert resp["result"]["tools"] == []

    def test_tools_list_with_registered(self):
        tool = Tool(name="hello", description="Says hello", input_schema={"type": "object"})
        register_tool(tool, lambda: "world")
        resp = self.server.handle_request(self._req("tools/list"))
        assert len(resp["result"]["tools"]) == 1
        assert resp["result"]["tools"][0]["name"] == "hello"

    def test_tools_call(self):
        tool = Tool(name="add", description="Adds two numbers", input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
        })
        register_tool(tool, lambda a, b: a + b)
        resp = self.server.handle_request(self._req("tools/call", {
            "name": "add", "arguments": {"a": 2, "b": 3},
        }))
        assert "5" in resp["result"]["content"][0]["text"]

    def test_tools_call_not_found(self):
        resp = self.server.handle_request(self._req("tools/call", {
            "name": "nonexistent", "arguments": {},
        }))
        assert resp["error"]["code"] == -32602
        assert "Tool not found" in resp["error"]["message"]

    def test_resources_list_empty(self):
        resp = self.server.handle_request(self._req("resources/list"))
        assert resp["result"]["resources"] == []

    def test_resources_list_with_registered(self):
        res = Resource(uri="nova://test", name="Test", description="Test resource")
        register_resource(res, lambda: {"data": 42})
        resp = self.server.handle_request(self._req("resources/list"))
        assert len(resp["result"]["resources"]) == 1
        assert resp["result"]["resources"][0]["uri"] == "nova://test"

    def test_resources_read(self):
        res = Resource(uri="nova://hello", name="Hello", description="Greeting")
        register_resource(res, lambda: {"message": "Hi!"})
        resp = self.server.handle_request(self._req("resources/read", {"uri": "nova://hello"}))
        assert resp["result"]["contents"][0]["uri"] == "nova://hello"
        assert '"Hi!"' in resp["result"]["contents"][0]["text"]

    def test_prompts_list(self):
        prompt = Prompt(name="test_prompt", description="Test", arguments=[])
        register_prompt(prompt, lambda: {})
        resp = self.server.handle_request(self._req("prompts/list"))
        assert len(resp["result"]["prompts"]) == 1

    def test_method_not_found(self):
        resp = self.server.handle_request(self._req("unknown_method"))
        assert resp["error"]["code"] == -32601
        assert "Method not found" in resp["error"]["message"]

    def test_handler_exception_returns_error(self):
        tool = Tool(name="broken", description="Always fails", input_schema={})
        register_tool(tool, lambda: (_ for _ in ()).throw(RuntimeError("oops")))
        resp = self.server.handle_request(self._req("tools/call", {
            "name": "broken", "arguments": {},
        }))
        assert resp["error"]["code"] == -32603
