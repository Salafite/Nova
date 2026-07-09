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
