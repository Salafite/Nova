import json
import os
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.auth.deps import get_current_user


@pytest.fixture
def auth_override():
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "test", "role": "admin"}
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


class MockChunk:
    def __init__(self, content=None, tool_calls=None):
        self.choices = [MagicMock()]
        delta = MagicMock()
        delta.content = content
        delta.tool_calls = tool_calls
        self.choices[0].delta = delta


class TestAiService:
    def test_stream_chat_no_api_key(self):
        os.environ.pop("OPENAI_API_KEY", None)
        from packages.ai.service import stream_chat
        events = list(stream_chat([], "hello"))
        joined = "".join(events)
        assert "error" in joined
        assert "done" in joined

    def test_stream_chat_text_only(self):
        os.environ["OPENAI_API_KEY"] = "sk-test"
        from packages.ai.service import stream_chat

        chunks = [MockChunk(content=c) for c in ["Hello", " ", "World"]]

        with patch("packages.ai.service.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            MockOpenAI.return_value = mock_client
            mock_client.chat.completions.create.return_value = chunks

            events = list(stream_chat([], "hello"))
        texts = []
        for e in events:
            if e.startswith("data: "):
                data = json.loads(e[6:].strip())
                if data["type"] == "text":
                    texts.append(data["content"])
        assert "".join(texts) == "Hello World"

    def test_stream_chat_tool_call_then_text(self):
        os.environ["OPENAI_API_KEY"] = "sk-test"
        from packages.ai.service import stream_chat

        tc = MagicMock()
        tc.index = 0
        tc.id = "call_1"
        tc.function.name = "list_products"
        tc.function.arguments = '{"limit": 5}'

        chunks_round1 = [MockChunk(content="Checking"), MockChunk(tool_calls=[tc])]
        chunks_round2 = [MockChunk(content="Found 5 products")]

        with (
            patch("packages.ai.service.OpenAI") as MockOpenAI,
            patch("packages.ai.service.call_tool") as mock_call_tool,
        ):
            mock_call_tool.return_value = [{"id": 1, "name": "Widget"}]
            mock_client = MagicMock()
            MockOpenAI.return_value = mock_client
            mock_client.chat.completions.create.side_effect = [chunks_round1, chunks_round2]

            events = list(stream_chat([], "list products"))
        texts = []
        event_types = []
        for e in events:
            if e.startswith("data: "):
                data = json.loads(e[6:].strip())
                event_types.append(data["type"])
                if data["type"] == "text":
                    texts.append(data["content"])
        assert "tool_start" in event_types
        assert "tool_end" in event_types
        assert "Found 5 products" in "".join(texts)
        mock_call_tool.assert_called_once_with("list_products", {"limit": 5}, user=None)

    def test_stream_chat_propagates_user_tenant_to_tool_call(self):
        os.environ["OPENAI_API_KEY"] = "sk-test"
        from packages.ai.service import stream_chat
        from modules.core.context import get_current_tenant

        user = {"id": 10, "username": "alice", "business_id": 42, "role": "User"}

        tc = MagicMock()
        tc.index = 0
        tc.id = "call_tenant_1"
        tc.function.name = "list_products"
        tc.function.arguments = '{"limit": 10}'

        chunks_round1 = [MockChunk(content="Checking"), MockChunk(tool_calls=[tc])]
        chunks_round2 = [MockChunk(content="Done")]

        with (
            patch("packages.ai.service.OpenAI") as MockOpenAI,
            patch("packages.ai.service.call_tool") as mock_call_tool,
        ):
            mock_call_tool.return_value = [{"id": 1, "name": "Widget", "business_id": 42}]
            mock_client = MagicMock()
            MockOpenAI.return_value = mock_client
            mock_client.chat.completions.create.side_effect = [chunks_round1, chunks_round2]

            events = list(stream_chat([], "list products", user=user))

        mock_call_tool.assert_called_once_with("list_products", {"limit": 10}, user=user)

    def test_stream_chat_tenant_context_active_during_tool_execution(self):
        os.environ["OPENAI_API_KEY"] = "sk-test"
        from packages.ai.service import stream_chat
        from packages.mcp.registry import register_tool, get_current_user as mcp_get_current_user
        from packages.mcp.types import Tool
        from modules.core.context import get_current_tenant

        observed = {}

        def _test_handler(limit=10):
            observed["tenant_id"] = get_current_tenant()
            observed["user"] = mcp_get_current_user()
            return {"status": "ok", "tenant": observed["tenant_id"]}

        test_tool = Tool(
            name="test_tenant_probe_tool",
            description="Probe active tenant context",
            input_schema={"type": "object", "properties": {"limit": {"type": "integer"}}},
            tier="tier1",
        )
        register_tool(test_tool, _test_handler)

        user = {"id": 99, "username": "charlie", "business_id": 777}

        tc = MagicMock()
        tc.index = 0
        tc.id = "call_probe_1"
        tc.function.name = "test_tenant_probe_tool"
        tc.function.arguments = '{"limit": 5}'

        chunks_round1 = [MockChunk(tool_calls=[tc])]
        chunks_round2 = [MockChunk(content="Probe complete")]

        with patch("packages.ai.service.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            MockOpenAI.return_value = mock_client
            mock_client.chat.completions.create.side_effect = [chunks_round1, chunks_round2]

            events = list(stream_chat([], "probe tenant", user=user))

        assert observed["tenant_id"] == 777
        assert observed["user"]["username"] == "charlie"
        assert observed["user"]["business_id"] == 777

    def test_stream_chat_tier2_tool_propose_action_stores_tenant_user(self):
        os.environ["OPENAI_API_KEY"] = "sk-test"
        from packages.ai.service import stream_chat
        from packages.mcp.registry import register_tool, _pending_actions
        from packages.mcp.types import Tool

        test_tool = Tool(
            name="delete_sensitive_record",
            description="Delete sensitive record",
            input_schema={"type": "object", "properties": {"id": {"type": "integer"}}},
            tier="tier2",
        )
        register_tool(test_tool, lambda id: {"deleted": id})

        user = {"id": 15, "username": "admin_user", "business_id": 88}

        tc = MagicMock()
        tc.index = 0
        tc.id = "call_del_1"
        tc.function.name = "delete_sensitive_record"
        tc.function.arguments = '{"id": 100}'

        chunks_round1 = [MockChunk(tool_calls=[tc])]
        chunks_round2 = [MockChunk(content="Action proposed")]

        with patch("packages.ai.service.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            MockOpenAI.return_value = mock_client
            mock_client.chat.completions.create.side_effect = [chunks_round1, chunks_round2]

            events = list(stream_chat([], "delete record 100", user=user))

        conf_events = []
        for e in events:
            if e.startswith("data: "):
                data = json.loads(e[6:].strip())
                if data["type"] == "confirmation_required":
                    conf_events.append(data)

        assert len(conf_events) == 1
        action_id = conf_events[0]["action_id"]
        assert conf_events[0]["tool"] == "delete_sensitive_record"
        assert action_id in _pending_actions
        assert _pending_actions[action_id]["user"]["business_id"] == 88

    def test_stream_chat_fallback_to_nova_tenant_id_env(self):
        os.environ["OPENAI_API_KEY"] = "sk-test"
        os.environ["NOVA_TENANT_ID"] = "555"
        try:
            from packages.ai.service import stream_chat
            from packages.mcp.registry import register_tool
            from packages.mcp.types import Tool
            from modules.core.context import get_current_tenant

            observed_tenant = []

            def _probe_handler():
                observed_tenant.append(get_current_tenant())
                return {"tenant": get_current_tenant()}

            probe_tool = Tool(
                name="env_tenant_probe_tool",
                description="Probe env tenant",
                input_schema={"type": "object"},
                tier="tier1",
            )
            register_tool(probe_tool, _probe_handler)

            tc = MagicMock()
            tc.index = 0
            tc.id = "call_env_1"
            tc.function.name = "env_tenant_probe_tool"
            tc.function.arguments = '{}'

            chunks_round1 = [MockChunk(tool_calls=[tc])]
            chunks_round2 = [MockChunk(content="Env probe done")]

            with patch("packages.ai.service.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                MockOpenAI.return_value = mock_client
                mock_client.chat.completions.create.side_effect = [chunks_round1, chunks_round2]

                events = list(stream_chat([], "probe env"))

            assert observed_tenant == [555]
        finally:
            os.environ.pop("NOVA_TENANT_ID", None)


class TestAiRouter:
    def test_chat_endpoint_requires_auth(self, client):
        os.environ["OPENAI_API_KEY"] = "sk-test"
        resp = client.post("/api/ai/chat", json={"message": "hello"})
        assert resp.status_code == 401

    def test_chat_endpoint_streams_response(self, client, auth_override):
        os.environ["OPENAI_API_KEY"] = "sk-test"

        chunks = [MockChunk(content=c) for c in ["Hello", "!"]]

        with patch("packages.ai.service.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            MockOpenAI.return_value = mock_client
            mock_client.chat.completions.create.return_value = chunks

            resp = client.post("/api/ai/chat", json={"message": "hello"},
                               headers={"Authorization": "Bearer test"})
            body = resp.text

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        assert "Hello" in body

    def test_chat_endpoint_propagates_authenticated_tenant_context(self, client):
        os.environ["OPENAI_API_KEY"] = "sk-test"

        app.dependency_overrides[get_current_user] = lambda: {
            "id": 42,
            "username": "tenant_user",
            "business_id": 999,
            "role": "manager",
        }
        try:
            from packages.mcp.registry import register_tool, get_current_user as mcp_get_current_user
            from packages.mcp.types import Tool
            from modules.core.context import get_current_tenant

            captured_context = {}

            def _tenant_check_tool():
                captured_context["tenant_id"] = get_current_tenant()
                captured_context["user"] = mcp_get_current_user()
                return {"tenant_id": get_current_tenant()}

            test_tool = Tool(
                name="router_tenant_check_tool",
                description="Check tenant context in router execution",
                input_schema={"type": "object"},
                tier="tier1",
            )
            register_tool(test_tool, _tenant_check_tool)

            tc = MagicMock()
            tc.index = 0
            tc.id = "call_router_1"
            tc.function.name = "router_tenant_check_tool"
            tc.function.arguments = '{}'

            chunks_round1 = [MockChunk(tool_calls=[tc])]
            chunks_round2 = [MockChunk(content="Tenant verified")]

            with patch("packages.ai.service.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                MockOpenAI.return_value = mock_client
                mock_client.chat.completions.create.side_effect = [chunks_round1, chunks_round2]

                resp = client.post("/api/ai/chat", json={"message": "check tenant"},
                                   headers={"Authorization": "Bearer test"})

            assert resp.status_code == 200
            assert captured_context.get("tenant_id") == 999
            assert captured_context.get("user", {}).get("username") == "tenant_user"
            assert captured_context.get("user", {}).get("business_id") == 999
        finally:
            app.dependency_overrides.clear()
