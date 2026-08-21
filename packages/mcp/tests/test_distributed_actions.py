"""Tests for distributed MCP pending actions with Redis backend.

Validates the complete propose -> confirm lifecycle across simulated
multiple worker processes, TTL expiration, single-execution guarantees,
and context preservation.
"""

import json
import pytest
from packages.mcp.registry import (
    register_tool,
    call_tool,
    propose_action,
    confirm_action,
    get_current_user,
    get_tools,
    _pending_actions,
    _tools,
)
from packages.mcp.types import Tool
from packages.redis.client import get_redis_client


class TestDistributedActions:
    def setup_method(self):
        _tools.clear()
        _pending_actions.clear()
        client = get_redis_client()
        try:
            client.flushdb()
        except Exception:
            pass

    def test_propose_stores_in_redis_with_ttl(self):
        tool = Tool(name="delete_item", description="Delete an item", input_schema={})
        register_tool(tool, lambda item_id: f"deleted {item_id}")

        result = propose_action("delete_item", {"item_id": 42})
        action_id = result["action_id"]

        client = get_redis_client()
        key = f"nova:mcp:action:{action_id}"
        raw = client.get(key)
        assert raw is not None

        payload = json.loads(raw) if isinstance(raw, str) else raw
        assert payload["action_id"] == action_id
        assert payload["tool_name"] == "delete_item"
        assert payload["arguments"] == {"item_id": 42}

        # Check TTL is set close to 300 seconds
        ttl = client.ttl(key)
        assert 0 < ttl <= 300

    def test_cross_worker_confirmation_without_local_memory(self):
        """Simulate Worker 1 proposing an action and Worker 2 confirming it."""
        # Setup tool on both workers
        tool = Tool(name="confirm_order", description="Confirm order", input_schema={})
        register_tool(tool, lambda order_id: {"status": "confirmed", "order_id": order_id})

        # Worker 1: propose action
        user = {"id": 7, "username": "sales_rep", "business_id": 101}
        from packages.mcp.registry import _current_user
        token = _current_user.set(user)
        try:
            proposal = propose_action("confirm_order", {"order_id": 999})
        finally:
            _current_user.reset(token)

        action_id = proposal["action_id"]

        # Simulate Worker 2 by clearing in-memory process state
        _pending_actions.clear()
        assert action_id not in _pending_actions

        # Worker 2: confirm action
        exec_result = confirm_action(action_id)
        assert exec_result == {"status": "confirmed", "order_id": 999}

        # Verify key was atomically removed from Redis
        client = get_redis_client()
        key = f"nova:mcp:action:{action_id}"
        assert client.get(key) is None

    def test_single_execution_guarantee(self):
        """Action cannot be confirmed more than once (atomic getdel)."""
        tool = Tool(name="cancel_order", description="Cancel order", input_schema={})
        register_tool(tool, lambda order_id: f"cancelled {order_id}")

        proposal = propose_action("cancel_order", {"order_id": 123})
        action_id = proposal["action_id"]

        # First confirmation succeeds
        res1 = confirm_action(action_id)
        assert res1 == "cancelled 123"

        # Second confirmation fails with ValueError
        with pytest.raises(ValueError, match="Action not found or expired"):
            confirm_action(action_id)

    def test_ttl_expiration(self):
        """Expired actions in Redis cannot be confirmed."""
        tool = Tool(name="delete_record", description="Delete record", input_schema={})
        register_tool(tool, lambda record_id: "done")

        proposal = propose_action("delete_record", {"record_id": 1})
        action_id = proposal["action_id"]

        # Artificially expire the key in Redis and in-memory
        client = get_redis_client()
        key = f"nova:mcp:action:{action_id}"
        client.delete(key)
        _pending_actions.clear()

        with pytest.raises(ValueError, match="Action not found or expired"):
            confirm_action(action_id)

    def test_user_context_preservation_across_workers(self):
        """User context attached during proposal is available to handler on confirmation."""
        captured_user = []
        tool = Tool(name="audit_op", description="Audit operation", input_schema={})
        register_tool(tool, lambda: captured_user.append(get_current_user()))

        from packages.mcp.registry import _current_user
        token = _current_user.set({"id": 42, "username": "bob", "business_id": 5})
        try:
            proposal = propose_action("audit_op", {})
        finally:
            _current_user.reset(token)

        action_id = proposal["action_id"]

        # Clear in-memory state on Worker 2
        _pending_actions.clear()

        # Worker 2 confirms without active user context in contextvar
        confirm_action(action_id)

        assert len(captured_user) == 1
        assert captured_user[0] == {"id": 42, "username": "bob", "business_id": 5}

    def test_meta_tool_confirm_action_integration(self):
        """Test confirming via the meta-tool confirm_action handler."""
        tool = Tool(name="wipe_data", description="Wipe data", input_schema={})
        register_tool(tool, lambda target: f"wiped {target}")

        proposal = propose_action("wipe_data", {"target": "cache"})
        action_id = proposal["action_id"]

        # Register confirm_action tool handler
        register_tool(
            Tool(
                name="confirm_action",
                description="Confirm a previously proposed action for execution.",
                input_schema={"type": "object", "properties": {"action_id": {"type": "string"}}, "required": ["action_id"]},
                tier="tier1",
            ),
            lambda action_id: confirm_action(action_id),
        )

        # Simulate Worker 2 executing the confirm_action MCP tool
        _pending_actions.clear()
        result = call_tool("confirm_action", {"action_id": action_id})
        assert result == "wiped cache"

    def test_corrupted_payload_handled_gracefully(self):
        """Corrupted JSON in Redis is handled gracefully as not found or expired."""
        client = get_redis_client()
        key = "nova:mcp:action:corrupt_action_id"
        client.set(key, "invalid-non-json-content", ex=300)

        with pytest.raises(ValueError, match="Action not found or expired"):
            confirm_action("corrupt_action_id")
