import json
from decimal import Decimal
from datetime import datetime, date

from packages.mcp.registry import (
    get_tools, call_tool,
    list_resources, read_resource,
    get_prompts, get_prompt,
)


def _json_safe(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (set,)):
        return list(obj)
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    raise TypeError(f'Object of type {type(obj)} is not JSON serializable')


class McpServer:
    def __init__(self, name: str, version: str = "1.0"):
        self.name = name
        self.version = version
        self._initialized = False

    def handle_request(self, raw: dict, user: dict | None = None) -> dict | None:
        method = raw.get("method")
        params = raw.get("params", {})
        req_id = raw.get("id")

        try:
            if method == "initialize":
                return self._result(req_id, {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {},
                    },
                    "serverInfo": {
                        "name": self.name,
                        "version": self.version,
                    },
                })
            elif method == "notifications/initialized":
                return None
            elif method == "ping":
                return self._result(req_id, {})
            elif method == "tools/list":
                tools = get_tools()
                return self._result(req_id, {
                    "tools": [t.model_dump() if hasattr(t, 'model_dump') else t for t in tools]
                })
            elif method == "tools/call":
                result = call_tool(params["name"], params.get("arguments", {}), user=user)
                text = json.dumps(result, default=_json_safe, indent=2)
                return self._result(req_id, {
                    "content": [{"type": "text", "text": text}]
                })
            elif method == "resources/list":
                resources = list_resources()
                return self._result(req_id, {
                    "resources": [r.model_dump() if hasattr(r, 'model_dump') else r for r in resources]
                })
            elif method == "resources/read":
                result = read_resource(params["uri"])
                text = json.dumps(result, default=_json_safe, indent=2)
                return self._result(req_id, {
                    "contents": [{"uri": params["uri"], "text": text}]
                })
            elif method == "prompts/list":
                prompts = get_prompts()
                return self._result(req_id, {
                    "prompts": [p.model_dump() if hasattr(p, 'model_dump') else p for p in prompts]
                })
            elif method == "prompts/get":
                result = get_prompt(params["name"], params.get("arguments"))
                return self._result(req_id, result)
            else:
                return self._error(req_id, -32601, f"Method not found: {method}")
        except ValueError as e:
            return self._error(req_id, -32602, str(e))
        except Exception as e:
            return self._error(req_id, -32603, str(e))

    def _result(self, req_id, data):
        return {"jsonrpc": "2.0", "id": req_id, "result": data}

    def _error(self, req_id, code, message):
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
