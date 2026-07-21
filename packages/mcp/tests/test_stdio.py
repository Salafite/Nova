import json
import io
import sys
from packages.mcp.server import McpServer
from packages.mcp.stdio import run_stdio
from packages.mcp.types import Tool
from packages.mcp.registry import register_tool


class TestStdioTransport:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()
        registry._resources.clear()
        registry._prompts.clear()
        self.server = McpServer(name="TestServer", version="1.0")

    def test_run_stdio_processes_requests(self):
        tool = Tool(name="ping_tool", description="Returns pong", input_schema={})
        register_tool(tool, lambda: "pong")

        stdin = io.StringIO(
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2024-11-05", "clientInfo": {"name": "test", "version": "1.0"},
            }}) + "\n" +
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}) + "\n" +
            json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/list"}) + "\n"
        )
        stdout = io.StringIO()

        old_stdin = sys.stdin
        old_stdout = sys.stdout
        sys.stdin = stdin
        sys.stdout = stdout
        try:
            run_stdio(self.server)
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

        lines = stdout.getvalue().strip().split("\n")
        assert len(lines) == 3

        init_resp = json.loads(lines[0])
        assert init_resp["id"] == 1
        assert init_resp["result"]["serverInfo"]["name"] == "TestServer"

        ping_resp = json.loads(lines[1])
        assert ping_resp["id"] == 2
        assert ping_resp["result"] == {}

        tools_resp = json.loads(lines[2])
        assert tools_resp["id"] == 3
        assert len(tools_resp["result"]["tools"]) == 1
