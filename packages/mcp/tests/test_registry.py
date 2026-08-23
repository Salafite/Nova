from packages.mcp.registry import (
    register_tool, register_resource, register_prompt,
    get_tools, call_tool, list_resources, read_resource,
    get_prompts, get_prompt, get_current_user,
    propose_action, confirm_action, _pending_actions,
)
from packages.mcp.types import Tool, Resource, Prompt, PromptArg


class TestRegistry:
    def setup_method(self):
        from packages.mcp import registry
        from packages.redis.client import get_redis_client
        registry._tools.clear()
        registry._resources.clear()
        registry._prompts.clear()
        _pending_actions.clear()
        try:
            get_redis_client().flushdb()
        except Exception:
            pass

    def test_register_and_list_tools(self):
        tool = Tool(name="hello", description="Says hello", input_schema={"type": "object"})
        register_tool(tool, lambda: "world")
        tools = get_tools()
        assert len(tools) == 1
        assert tools[0].name == "hello"

    def test_call_tool(self):
        tool = Tool(name="greet", description="Greets", input_schema={"type": "object"})
        register_tool(tool, lambda name: f"Hello, {name}!")
        result = call_tool("greet", {"name": "Nova"})
        assert result == "Hello, Nova!"

    def test_call_tool_not_found(self):
        import pytest
        with pytest.raises(ValueError, match="Tool not found: unknown"):
            call_tool("unknown", {})

    def test_call_tool_with_user_context(self):
        captured = []
        tool = Tool(name="whoami", description="Returns user context", input_schema={})
        register_tool(tool, lambda: captured.append(get_current_user()))
        user = {"id": 1, "username": "alice", "business_id": 42}
        call_tool("whoami", {}, user=user)
        assert len(captured) == 1
        assert captured[0]["id"] == 1
        assert captured[0]["business_id"] == 42

    def test_call_tool_without_user_context_is_none(self):
        captured = []
        tool = Tool(name="whoami", description="Returns user", input_schema={})
        register_tool(tool, lambda: captured.append(get_current_user()))
        call_tool("whoami", {})
        assert len(captured) == 1
        assert captured[0] is None

    def test_user_context_resets_after_call(self):
        tool = Tool(name="echo", description="Echo", input_schema={})
        register_tool(tool, lambda: get_current_user())
        call_tool("echo", {}, user={"id": 1})
        assert get_current_user() is None

    def test_call_tool_sets_and_resets_tenant_context(self):
        from modules.core.context import get_current_tenant
        captured_tenant = []
        tool = Tool(name="tenant_tool", description="Checks tenant", input_schema={})
        register_tool(tool, lambda: captured_tenant.append(get_current_tenant()))
        user = {"id": 1, "username": "alice", "business_id": 42}
        call_tool("tenant_tool", {}, user=user)
        assert captured_tenant == [42]
        assert get_current_tenant() is None

    def test_call_tool_with_tenant_id_key(self):
        from modules.core.context import get_current_tenant
        captured_tenant = []
        tool = Tool(name="tenant_tool", description="Checks tenant", input_schema={})
        register_tool(tool, lambda: captured_tenant.append(get_current_tenant()))
        user = {"id": 1, "username": "alice", "tenant_id": 99}
        call_tool("tenant_tool", {}, user=user)
        assert captured_tenant == [99]
        assert get_current_tenant() is None

    def test_call_tool_with_nova_tenant_id_env_var(self, monkeypatch):
        from modules.core.context import get_current_tenant
        monkeypatch.setenv("NOVA_TENANT_ID", "77")
        captured_tenant = []
        tool = Tool(name="tenant_tool", description="Checks tenant", input_schema={})
        register_tool(tool, lambda: captured_tenant.append(get_current_tenant()))
        call_tool("tenant_tool", {})
        assert captured_tenant == [77]
        assert get_current_tenant() is None

    def test_call_tool_user_overrides_nova_tenant_id_env_var(self, monkeypatch):
        from modules.core.context import get_current_tenant
        monkeypatch.setenv("NOVA_TENANT_ID", "77")
        captured_tenant = []
        tool = Tool(name="tenant_tool", description="Checks tenant", input_schema={})
        register_tool(tool, lambda: captured_tenant.append(get_current_tenant()))
        user = {"id": 1, "business_id": 100}
        call_tool("tenant_tool", {}, user=user)
        assert captured_tenant == [100]
        assert get_current_tenant() is None

    def test_call_tool_exception_resets_tenant_context(self):
        import pytest
        from modules.core.context import get_current_tenant
        def _failing_handler():
            assert get_current_tenant() == 42
            raise RuntimeError("handler failed")
        tool = Tool(name="fail_tool", description="Fails", input_schema={})
        register_tool(tool, _failing_handler)
        with pytest.raises(RuntimeError, match="handler failed"):
            call_tool("fail_tool", {}, user={"business_id": 42})
        assert get_current_tenant() is None
        assert get_current_user() is None

    def test_propose_action_returns_preview(self):
        tool = Tool(name="test_tool_name", description="Test", input_schema={})
        register_tool(tool, lambda: "executed")
        result = propose_action("test_tool_name", {"key": "val"})
        assert "action_id" in result
        assert result["tool"] == "test_tool_name"
        assert "preview" in result

    def test_confirm_action_executes(self):
        tool = Tool(name="test_tool_name", description="Test", input_schema={})
        register_tool(tool, lambda: "executed_result")
        proposal = propose_action("test_tool_name", {})
        result = confirm_action(proposal["action_id"])
        assert result == "executed_result"

    def test_confirm_action_not_found(self):
        import pytest
        with pytest.raises(ValueError, match="Action not found or expired"):
            confirm_action("nonexistent")

    def test_propose_tool_not_found(self):
        import pytest
        with pytest.raises(ValueError, match="Tool not found: unknown"):
            propose_action("unknown", {})

    def test_register_and_list_resources(self):
        res = Resource(uri="nova://test", name="Test", description="A test resource")
        register_resource(res, lambda: {"key": "value"})
        resources = list_resources()
        assert len(resources) == 1
        assert resources[0].uri == "nova://test"

    def test_read_resource(self):
        res = Resource(uri="nova://hello", name="Hello", description="Greeting")
        register_resource(res, lambda: {"message": "Hi!"})
        result = read_resource("nova://hello")
        assert result == {"message": "Hi!"}

    def test_read_resource_not_found(self):
        import pytest
        with pytest.raises(ValueError, match="Resource not found: nova://missing"):
            read_resource("nova://missing")

    def test_register_and_list_prompts(self):
        prompt = Prompt(name="check_stock", description="Check stock of product", arguments=[
            PromptArg(name="product", description="Product name", required=True),
        ])
        register_prompt(prompt, lambda product: {"messages": [{"role": "user", "content": f"Check stock for {product}"}]})
        prompts = get_prompts()
        assert len(prompts) == 1
        assert prompts[0].name == "check_stock"

    def test_get_prompt(self):
        prompt = Prompt(name="hello_prompt", description="Says hello", arguments=[])
        register_prompt(prompt, lambda: {"messages": [{"role": "user", "content": "Hello!"}]})
        result = get_prompt("hello_prompt")
        assert result["messages"][0]["content"] == "Hello!"

    def test_get_prompt_not_found(self):
        import pytest
        with pytest.raises(ValueError, match="Prompt not found: unknown"):
            get_prompt("unknown")
