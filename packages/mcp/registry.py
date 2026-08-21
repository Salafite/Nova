import json
import time
import uuid
import logging
import contextvars
from packages.mcp.types import Tool, Resource, Prompt
from packages.redis.client import get_redis_client


logger = logging.getLogger("mcp.audit")

_tools: dict[str, dict] = {}
_resources: dict[str, dict] = {}
_prompts: dict[str, dict] = {}
_pending_actions: dict[str, dict] = {}
_ACTION_TTL = 300
_ACTION_KEY_PREFIX = "nova:mcp:action:"
_CONFIRM_ACTION_REGISTERED = False

# Context variable for the current user, set before handler execution
_current_user: contextvars.ContextVar[dict | None] = contextvars.ContextVar("current_user", default=None)


def _get_action_key(action_id: str) -> str:
    """Return the Redis key for a pending MCP action."""
    return f"{_ACTION_KEY_PREFIX}{action_id}"



def get_current_user() -> dict | None:
    """Return the current user dict for the active MCP tool call, or None if no user context.
    Tool handlers can call this to access the authenticated user.
    """
    return _current_user.get()


def register_tool(tool: Tool, handler):
    _tools[tool.name] = {"tool": tool, "handler": handler}


def register_resource(resource: Resource, handler):
    _resources[resource.uri] = {"resource": resource, "handler": handler}


def register_prompt(prompt: Prompt, handler):
    _prompts[prompt.name] = {"prompt": prompt, "handler": handler}


def get_tools() -> list[Tool]:
    _ensure_meta_tools()
    return [v["tool"] for v in _tools.values()]


def call_tool(name: str, arguments: dict, user: dict | None = None):
    entry = _tools.get(name)
    if not entry:
        raise ValueError(f"Tool not found: {name}")

    start = time.time()
    token = _current_user.set(user)
    try:
        result = entry["handler"](**arguments)
        elapsed = time.time() - start
        logger.info(
            "tool=%s user=%s tenant=%s status=success latency_ms=%d",
            name, user.get("id") if user else None,
            user.get("business_id") if user else None,
            round(elapsed * 1000),
        )
        return result
    except Exception as e:
        elapsed = time.time() - start
        logger.error(
            "tool=%s user=%s tenant=%s status=error error=%s latency_ms=%d",
            name, user.get("id") if user else None,
            user.get("business_id") if user else None,
            str(e), round(elapsed * 1000),
        )
        raise
    finally:
        _current_user.reset(token)


def propose_action(tool_name: str, arguments: dict) -> dict:
    """Propose a tier-2 action without executing it. Returns an action_id and preview."""
    entry = _tools.get(tool_name)
    if not entry:
        raise ValueError(f"Tool not found: {tool_name}")
    action_id = str(uuid.uuid4())
    now = time.time()
    user = _current_user.get()
    payload = {
        "action_id": action_id,
        "tool_name": tool_name,
        "arguments": arguments,
        "created_at": now,
        "timestamp": now,
        "user": user,
    }
    client = get_redis_client()
    key = _get_action_key(action_id)
    client.set(key, json.dumps(payload), ex=_ACTION_TTL)
    _pending_actions[action_id] = payload
    return {
        "action_id": action_id,
        "tool": tool_name,
        "preview": f"Action: {tool_name}\nArguments: {json.dumps(arguments, indent=2)}",
    }


def _fetch_and_delete_action(action_id: str) -> dict | None:
    """Atomically fetch and delete pending action payload from Redis or in-memory fallback."""
    client = get_redis_client()
    key = _get_action_key(action_id)
    raw = None
    try:
        raw = client.getdel(key)
    except Exception:
        try:
            pipe = client.pipeline()
            pipe.get(key)
            pipe.delete(key)
            results = pipe.execute()
            raw = results[0] if results else None
        except Exception:
            raw = None

    if not raw:
        _purge_expired_actions()
        return _pending_actions.pop(action_id, None)

    _pending_actions.pop(action_id, None)
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def confirm_action(action_id: str) -> dict:
    """Confirm and execute a previously proposed action."""
    entry = _fetch_and_delete_action(action_id)
    if not entry:
        raise ValueError(f"Action not found or expired: {action_id}")
    user = _current_user.get() or entry.get("user")
    return call_tool(entry["tool_name"], entry["arguments"], user=user)


def _purge_expired_actions():
    now = time.time()
    expired = [aid for aid, a in _pending_actions.items()
               if now - a.get("created_at", a.get("timestamp", 0)) > _ACTION_TTL]
    for aid in expired:
        _pending_actions.pop(aid, None)


def list_resources() -> list[Resource]:
    return [v["resource"] for v in _resources.values()]


def read_resource(uri: str):
    entry = _resources.get(uri)
    if not entry:
        raise ValueError(f"Resource not found: {uri}")
    token = _current_user.set({})
    try:
        return entry["handler"]()
    finally:
        _current_user.reset(token)


def get_prompts() -> list[Prompt]:
    return [v["prompt"] for v in _prompts.values()]


def get_prompt(name: str, arguments: dict = None):
    entry = _prompts.get(name)
    if not entry:
        raise ValueError(f"Prompt not found: {name}")
    return entry["handler"](**(arguments or {}))


def _ensure_meta_tools():
    """Register meta-tools like confirm_action once."""
    global _CONFIRM_ACTION_REGISTERED
    if _CONFIRM_ACTION_REGISTERED:
        return
    _CONFIRM_ACTION_REGISTERED = True

    def _handle_confirm_action(action_id: str):
        entry = _fetch_and_delete_action(action_id)
        if not entry:
            raise ValueError(f"Action not found or expired: {action_id}")
        tool_entry = _tools.get(entry["tool_name"])
        if not tool_entry:
            raise ValueError(f"Original tool not found: {entry['tool_name']}")
        user = _current_user.get() or entry.get("user")
        token = _current_user.set(user)
        try:
            return tool_entry["handler"](**entry["arguments"])
        finally:
            _current_user.reset(token)

    register_tool(
        Tool(
            name="confirm_action",
            description="Confirm a previously proposed action for execution. Use this when the user has approved a proposed action that requires confirmation.",
            input_schema={
                "type": "object",
                "properties": {
                    "action_id": {
                        "type": "string",
                        "description": "The action_id from a previously proposed action",
                    },
                },
                "required": ["action_id"],
            },
            tier="tier1",
        ),
        _handle_confirm_action,
    )
