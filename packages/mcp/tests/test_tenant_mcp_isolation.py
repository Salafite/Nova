"""MCP Multi-Tenant Isolation Integration Tests.

Verifies tenant data isolation and business context propagation across:
1. Stdio transport (env vars, user dict, subprocess e2e, Tier 2 propose/confirm)
2. SSE transport (multi-session isolation, interleaved messaging, resources, mutations)
3. In-App AI Assistant (POST /api/ai/chat, streaming tool calls, chained tools, Tier 2 proposals)
4. Cross-domain MCP servers (all 15 servers scoped to active tenant context)
"""

import asyncio
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.main import app as main_app
from modules.core.context import (
    clear_current_tenant,
    get_current_tenant,
    tenant_context,
)
from packages.auth.deps import get_current_user as auth_get_current_user
from packages.auth.jwt import create_access_token
from packages.mcp import registry
from packages.mcp.registry import (
    _pending_actions,
    _prompts,
    _resources,
    _tools,
    call_tool,
    confirm_action,
    get_current_user as mcp_get_current_user,
    propose_action,
    register_resource,
    register_tool,
)
from packages.mcp.router import create_mcp_router
from packages.mcp.server import McpServer
from packages.mcp.servers import (
    accounting_mcp,
    admin_mcp,
    bi_mcp,
    crm_mcp,
    database_mcp,
    hr_mcp,
    inventory_mcp,
    maintenance_mcp,
    manufacturing_mcp,
    notifications_mcp,
    pos_mcp,
    projects_mcp,
    purchasing_mcp,
    sales_mcp,
    warehouse_mcp,
)
from packages.mcp.sse import _sessions, handle_message, sse_connection
from packages.mcp.stdio import run_stdio
from packages.mcp.types import Resource, Tool

ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _req(method: str, params: dict | None = None, req_id: int = 1) -> dict:
    msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params:
        msg["params"] = params
    return msg


class MockChunk:
    def __init__(self, content=None, tool_calls=None):
        self.choices = [MagicMock()]
        delta = MagicMock()
        delta.content = content
        delta.tool_calls = tool_calls
        self.choices[0].delta = delta


@pytest.fixture(autouse=True)
def cleanup_mcp_state():
    _tools.clear()
    _resources.clear()
    _prompts.clear()
    _pending_actions.clear()
    _sessions.clear()
    clear_current_tenant()
    yield
    _tools.clear()
    _resources.clear()
    _prompts.clear()
    _pending_actions.clear()
    _sessions.clear()
    clear_current_tenant()


# ============================================================================
# 1. Stdio Transport Multi-Tenant Isolation Tests
# ============================================================================


class TestStdioTenantIsolation:
    """Test tenant isolation over MCP stdio transport."""

    def test_stdio_env_var_scopes_crud_and_custom_queries(self, monkeypatch):
        """Verify NOVA_TENANT_ID environment variable sets tenant context during stdio execution."""
        inventory_mcp.register_tools()
        sales_mcp.register_tools()

        server = McpServer(name="inventory-sales-stdio", version="1.0")

        # Set tenant to 101
        monkeypatch.setenv("NOVA_TENANT_ID", "101")

        captured_tenants = []

        def spy_list_products(*args, **kwargs):
            captured_tenants.append(("list_products", get_current_tenant()))
            return [{"id": 1, "name": "Tenant 101 Product", "business_id": 101}]

        def spy_list_orders(*args, **kwargs):
            captured_tenants.append(("list_orders", get_current_tenant()))
            return [{"id": 10, "order_number": "SO-101", "business_id": 101}]

        with (
            patch.object(inventory_mcp._products_svc, "list", side_effect=spy_list_products),
            patch.object(sales_mcp._orders_svc, "list", side_effect=spy_list_orders),
        ):
            stdin = io.StringIO(
                json.dumps(_req("tools/call", {"name": "list_products", "arguments": {}}, req_id=1)) + "\n" +
                json.dumps(_req("tools/call", {"name": "list_orders", "arguments": {}}, req_id=2)) + "\n"
            )
            stdout = io.StringIO()

            old_stdin, old_stdout = sys.stdin, sys.stdout
            sys.stdin, sys.stdout = stdin, stdout
            try:
                run_stdio(server)
            finally:
                sys.stdin, sys.stdout = old_stdin, old_stdout

        lines = [json.loads(line) for line in stdout.getvalue().strip().split("\n") if line.strip()]
        assert len(lines) == 2
        assert lines[0]["id"] == 1
        assert "Tenant 101 Product" in lines[0]["result"]["content"][0]["text"]
        assert lines[1]["id"] == 2
        assert "SO-101" in lines[1]["result"]["content"][0]["text"]

        assert captured_tenants == [
            ("list_products", 101),
            ("list_orders", 101),
        ]
        # Tenant context should be cleanly restored/cleared after stdio completes
        assert get_current_tenant() is None

    def test_stdio_switching_tenant_env_var_isolates_data(self, monkeypatch):
        """Verify different NOVA_TENANT_ID values switch the data scope for stdio requests."""
        inventory_mcp.register_tools()
        server = McpServer(name="inventory-stdio", version="1.0")

        # First run under Tenant 201
        monkeypatch.setenv("NOVA_TENANT_ID", "201")
        captured_201 = []

        def spy_create_201(payload):
            captured_201.append((get_current_tenant(), payload))
            return {"id": 1, "name": payload["name"], "business_id": get_current_tenant()}

        with patch.object(inventory_mcp._products_svc, "create", side_effect=spy_create_201):
            stdin = io.StringIO(
                json.dumps(_req("tools/call", {
                    "name": "create_product",
                    "arguments": {"name": "Product A", "sku": "SKU-A"},
                }, req_id=1)) + "\n"
            )
            stdout = io.StringIO()
            old_stdin, old_stdout = sys.stdin, sys.stdout
            sys.stdin, sys.stdout = stdin, stdout
            try:
                run_stdio(server)
            finally:
                sys.stdin, sys.stdout = old_stdin, old_stdout

        assert len(captured_201) == 1
        assert captured_201[0][0] == 201

        # Second run under Tenant 202
        monkeypatch.setenv("NOVA_TENANT_ID", "202")
        captured_202 = []

        def spy_create_202(payload):
            captured_202.append((get_current_tenant(), payload))
            return {"id": 2, "name": payload["name"], "business_id": get_current_tenant()}

        with patch.object(inventory_mcp._products_svc, "create", side_effect=spy_create_202):
            stdin = io.StringIO(
                json.dumps(_req("tools/call", {
                    "name": "create_product",
                    "arguments": {"name": "Product B", "sku": "SKU-B"},
                }, req_id=2)) + "\n"
            )
            stdout = io.StringIO()
            old_stdin, old_stdout = sys.stdin, sys.stdout
            sys.stdin, sys.stdout = stdin, stdout
            try:
                run_stdio(server)
            finally:
                sys.stdin, sys.stdout = old_stdin, old_stdout

        assert len(captured_202) == 1
        assert captured_202[0][0] == 202

    def test_stdio_user_dict_tenant_scoping(self):
        """Verify passing user dictionary with business_id sets the active tenant."""
        accounting_mcp.register_tools()
        server = McpServer(name="accounting-stdio", version="1.0")

        observed_tenant = []

        def spy_list_invoices(*args, **kwargs):
            observed_tenant.append(get_current_tenant())
            return [{"id": 50, "invoice_number": "INV-50", "business_id": get_current_tenant()}]

        with patch.object(accounting_mcp._inv_svc, "list", side_effect=spy_list_invoices):
            stdin = io.StringIO(
                json.dumps(_req("tools/call", {"name": "list_invoices", "arguments": {}}, req_id=1)) + "\n"
            )
            stdout = io.StringIO()
            old_stdin, old_stdout = sys.stdin, sys.stdout
            sys.stdin, sys.stdout = stdin, stdout
            try:
                run_stdio(server, user={"id": 7, "username": "accountant", "business_id": 555})
            finally:
                sys.stdin, sys.stdout = old_stdin, old_stdout

        assert observed_tenant == [555]

    def test_stdio_resource_reading_tenant_scoping(self, monkeypatch):
        """Verify resources read via stdio execute in the active tenant context."""
        inventory_mcp.register_tools()
        server = McpServer(name="resource-test", version="1.0")

        monkeypatch.setenv("NOVA_TENANT_ID", "888")

        observed_tenant = []

        def spy_list_products(*args, **kwargs):
            observed_tenant.append(get_current_tenant())
            return [{"id": 1, "name": "Resource Item", "business_id": 888}]

        with patch.object(inventory_mcp._products_svc, "list", side_effect=spy_list_products):
            stdin = io.StringIO(
                json.dumps(_req("resources/read", {"uri": "nova://inventory/products"}, req_id=1)) + "\n"
            )
            stdout = io.StringIO()
            old_stdin, old_stdout = sys.stdin, sys.stdout
            sys.stdin, sys.stdout = stdin, stdout
            try:
                run_stdio(server)
            finally:
                sys.stdin, sys.stdout = old_stdin, old_stdout

        resp = json.loads(stdout.getvalue().strip())
        assert resp["id"] == 1
        assert "Resource Item" in resp["result"]["contents"][0]["text"]
        assert observed_tenant == [888]

    def test_stdio_subprocess_e2e_tenant_isolation(self):
        """Verify end-to-end subprocess MCP server launch with NOVA_TENANT_ID environment variable."""
        proc = subprocess.Popen(
            [
                sys.executable, "-c",
                f"import sys; sys.path.insert(0, r'{ROOT}'); "
                f"from packages.mcp.servers.inventory_mcp import register_tools; "
                f"from packages.mcp.server import McpServer; "
                f"from packages.mcp.stdio import run_stdio; "
                f"register_tools(); "
                f"run_stdio(McpServer(name='test-e2e', version='1.0'))",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "NOVA_TENANT_ID": "77"},
        )
        reqs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2024-11-05", "clientInfo": {"name": "test", "version": "1.0"},
            }},
            {"jsonrpc": "2.0", "id": 2, "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
        ]
        input_lines = "\n".join(json.dumps(r) for r in reqs)
        stdout, stderr = proc.communicate(input=input_lines, timeout=10)
        assert proc.returncode == 0
        responses = [json.loads(line) for line in stdout.strip().split("\n") if line.strip()]
        assert len(responses) >= 2
        assert responses[0]["id"] == 1
        assert responses[1]["id"] == 3
        tool_names = [t["name"] for t in responses[1]["result"]["tools"]]
        assert "list_products" in tool_names


# ============================================================================
# 2. SSE Transport Multi-Tenant Isolation Tests
# ============================================================================


class TestSseTenantIsolation:
    """Test tenant isolation over MCP SSE transport."""

    def setup_method(self):
        self.server = McpServer(name="TestSSEIsolation", version="1.0")
        inventory_mcp.register_tools()
        sales_mcp.register_tools()
        accounting_mcp.register_tools()

    def test_sse_multi_session_tenant_isolation(self):
        """Verify concurrent/distinct SSE sessions execute tools in their own tenant contexts."""
        sid_tenant_a = "session-tenant-100"
        sid_tenant_b = "session-tenant-200"

        user_a = {"id": 1, "username": "alice", "business_id": 100, "role": "admin"}
        user_b = {"id": 2, "username": "bob", "business_id": 200, "role": "admin"}

        _sessions[sid_tenant_a] = {"queue": asyncio.Queue(), "user": user_a}
        _sessions[sid_tenant_b] = {"queue": asyncio.Queue(), "user": user_b}

        observed_queries = []

        def spy_list_products(*args, **kwargs):
            current_t = get_current_tenant()
            observed_queries.append(("list_products", current_t))
            return [{"id": current_t, "name": f"Product Tenant {current_t}", "business_id": current_t}]

        def spy_list_orders(*args, **kwargs):
            current_t = get_current_tenant()
            observed_queries.append(("list_orders", current_t))
            return [{"id": current_t * 10, "order_number": f"SO-{current_t}", "business_id": current_t}]

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with (
                patch.object(inventory_mcp._products_svc, "list", side_effect=spy_list_products),
                patch.object(sales_mcp._orders_svc, "list", side_effect=spy_list_orders),
            ):
                # Interleaved message handling
                loop.run_until_complete(handle_message(sid_tenant_a, {
                    "jsonrpc": "2.0", "id": 101, "method": "tools/call",
                    "params": {"name": "list_products", "arguments": {}},
                }, self.server))

                loop.run_until_complete(handle_message(sid_tenant_b, {
                    "jsonrpc": "2.0", "id": 201, "method": "tools/call",
                    "params": {"name": "list_products", "arguments": {}},
                }, self.server))

                loop.run_until_complete(handle_message(sid_tenant_a, {
                    "jsonrpc": "2.0", "id": 102, "method": "tools/call",
                    "params": {"name": "list_orders", "arguments": {}},
                }, self.server))

                loop.run_until_complete(handle_message(sid_tenant_b, {
                    "jsonrpc": "2.0", "id": 202, "method": "tools/call",
                    "params": {"name": "list_orders", "arguments": {}},
                }, self.server))

                # Retrieve responses from Session A queue
                resp_a1 = loop.run_until_complete(_sessions[sid_tenant_a]["queue"].get())
                resp_a2 = loop.run_until_complete(_sessions[sid_tenant_a]["queue"].get())

                # Retrieve responses from Session B queue
                resp_b1 = loop.run_until_complete(_sessions[sid_tenant_b]["queue"].get())
                resp_b2 = loop.run_until_complete(_sessions[sid_tenant_b]["queue"].get())

                # Validate Session A content
                assert resp_a1["id"] == 101
                assert "Product Tenant 100" in resp_a1["result"]["content"][0]["text"]
                assert resp_a2["id"] == 102
                assert "SO-100" in resp_a2["result"]["content"][0]["text"]

                # Validate Session B content
                assert resp_b1["id"] == 201
                assert "Product Tenant 200" in resp_b1["result"]["content"][0]["text"]
                assert resp_b2["id"] == 202
                assert "SO-200" in resp_b2["result"]["content"][0]["text"]

                # Verify exact tenant execution sequence
                assert observed_queries == [
                    ("list_products", 100),
                    ("list_products", 200),
                    ("list_orders", 100),
                    ("list_orders", 200),
                ]
        finally:
            loop.close()
            _sessions.pop(sid_tenant_a, None)
            _sessions.pop(sid_tenant_b, None)

    def test_sse_mutations_and_scoping_isolation(self):
        """Verify data created or modified in one SSE session is strictly scoped to that tenant."""
        sid_1 = "sess-mut-1"
        sid_2 = "sess-mut-2"

        _sessions[sid_1] = {"queue": asyncio.Queue(), "user": {"id": 10, "business_id": 301}}
        _sessions[sid_2] = {"queue": asyncio.Queue(), "user": {"id": 20, "business_id": 302}}

        created_records = []

        def spy_create_order(payload):
            tenant = get_current_tenant()
            record = {"id": len(created_records) + 1, "customer_id": payload["customer_id"], "business_id": tenant}
            created_records.append(record)
            return record

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with patch.object(sales_mcp._orders_svc, "create", side_effect=spy_create_order):
                loop.run_until_complete(handle_message(sid_1, {
                    "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                    "params": {"name": "create_order", "arguments": {"customer_id": 99}},
                }, self.server))

                loop.run_until_complete(handle_message(sid_2, {
                    "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": "create_order", "arguments": {"customer_id": 88}},
                }, self.server))

                resp1 = loop.run_until_complete(_sessions[sid_1]["queue"].get())
                resp2 = loop.run_until_complete(_sessions[sid_2]["queue"].get())

                assert resp1["id"] == 1
                assert resp2["id"] == 2

                assert len(created_records) == 2
                assert created_records[0]["business_id"] == 301
                assert created_records[0]["customer_id"] == 99
                assert created_records[1]["business_id"] == 302
                assert created_records[1]["customer_id"] == 88
        finally:
            loop.close()
            _sessions.pop(sid_1, None)
            _sessions.pop(sid_2, None)

    def test_sse_resource_reading_isolation(self):
        """Verify reading resources over SSE returns data scoped to each session's tenant."""
        sid_x = "sess-res-x"
        sid_y = "sess-res-y"

        _sessions[sid_x] = {"queue": asyncio.Queue(), "user": {"id": 1, "business_id": 501}}
        _sessions[sid_y] = {"queue": asyncio.Queue(), "user": {"id": 2, "business_id": 502}}

        captured_resource_tenants = []

        def spy_list_products(*args, **kwargs):
            t = get_current_tenant()
            captured_resource_tenants.append(t)
            return [{"id": 1, "name": f"Item for {t}", "business_id": t}]

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with patch.object(inventory_mcp._products_svc, "list", side_effect=spy_list_products):
                loop.run_until_complete(handle_message(sid_x, {
                    "jsonrpc": "2.0", "id": 11, "method": "resources/read",
                    "params": {"uri": "nova://inventory/products"},
                }, self.server))

                loop.run_until_complete(handle_message(sid_y, {
                    "jsonrpc": "2.0", "id": 22, "method": "resources/read",
                    "params": {"uri": "nova://inventory/products"},
                }, self.server))

                resp_x = loop.run_until_complete(_sessions[sid_x]["queue"].get())
                resp_y = loop.run_until_complete(_sessions[sid_y]["queue"].get())

                assert "Item for 501" in resp_x["result"]["contents"][0]["text"]
                assert "Item for 502" in resp_y["result"]["contents"][0]["text"]
                assert captured_resource_tenants == [501, 502]
        finally:
            loop.close()
            _sessions.pop(sid_x, None)
            _sessions.pop(sid_y, None)

    def test_sse_tier2_propose_and_confirm_multi_tenant(self):
        """Verify proposing and confirming Tier 2 actions across multiple SSE sessions maintains tenant context."""
        sid_1 = "sess-tier2-1"
        sid_2 = "sess-tier2-2"

        _sessions[sid_1] = {"queue": asyncio.Queue(), "user": {"id": 101, "business_id": 701}}
        _sessions[sid_2] = {"queue": asyncio.Queue(), "user": {"id": 102, "business_id": 702}}

        deleted_records = []

        def spy_delete_product(product_id):
            tenant = get_current_tenant()
            deleted_records.append((product_id, tenant))
            return {"deleted": True, "id": product_id, "business_id": tenant}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with patch.object(inventory_mcp._products_svc, "delete", side_effect=spy_delete_product):
                # Tenant 701 proposes deleting product 10
                action_1 = propose_action("delete_product", {"id": 10}, user=_sessions[sid_1]["user"])
                aid_1 = action_1["action_id"]

                # Tenant 702 proposes deleting product 20
                action_2 = propose_action("delete_product", {"id": 20}, user=_sessions[sid_2]["user"])
                aid_2 = action_2["action_id"]

                assert _pending_actions[aid_1]["user"]["business_id"] == 701
                assert _pending_actions[aid_2]["user"]["business_id"] == 702

                # Confirm action 1 through Session 1
                res_1 = confirm_action(aid_1)
                # Confirm action 2 through Session 2
                res_2 = confirm_action(aid_2)

                assert res_1["business_id"] == 701
                assert res_2["business_id"] == 702
                assert deleted_records == [(10, 701), (20, 702)]
        finally:
            loop.close()
            _sessions.pop(sid_1, None)
            _sessions.pop(sid_2, None)

    def test_sse_endpoint_fastapi_integration(self):
        """Verify FastAPI SSE endpoint propagates user authorization and tenant context."""
        fastapi_app = FastAPI()
        user_override = {"id": 5, "username": "sse_user", "business_id": 999, "role": "admin"}
        fastapi_app.dependency_overrides[auth_get_current_user] = lambda: user_override
        fastapi_app.include_router(create_mcp_router(self.server))

        client = TestClient(fastapi_app)

        observed_tenants = []

        def spy_list_customers(*args, **kwargs):
            observed_tenants.append(get_current_tenant())
            return [{"id": 1, "customer_name": "Tenant 999 Corp", "business_id": 999}]

        with patch.object(sales_mcp._customers_svc, "list", side_effect=spy_list_customers):
            # Connect SSE session
            sess_id = "test-fastapi-sess"
            _sessions[sess_id] = {"queue": asyncio.Queue(), "user": user_override}

            # Post message to session
            resp = client.post(
                f"/mcp/message?session_id={sess_id}",
                json=_req("tools/call", {"name": "list_customers", "arguments": {}}, req_id=42),
                headers={"Authorization": "Bearer test-token"},
            )
            assert resp.status_code == 200
            assert resp.json() == {"ok": True}

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                msg = loop.run_until_complete(_sessions[sess_id]["queue"].get())
                assert msg["id"] == 42
                assert "Tenant 999 Corp" in msg["result"]["content"][0]["text"]
                assert observed_tenants == [999]
            finally:
                loop.close()
                _sessions.pop(sess_id, None)


# ============================================================================
# 3. In-App AI Assistant Multi-Tenant Isolation Tests
# ============================================================================


class TestAiAssistantTenantIsolation:
    """Test tenant isolation for in-app AI assistant (/api/ai/chat and stream_chat)."""

    def setup_method(self):
        inventory_mcp.register_tools()
        sales_mcp.register_tools()
        accounting_mcp.register_tools()
        purchasing_mcp.register_tools()
        os.environ["OPENAI_API_KEY"] = "sk-test"

    def teardown_method(self):
        os.environ.pop("OPENAI_API_KEY", None)

    def test_ai_chat_single_tool_tenant_scoping(self):
        """Verify AI chat tool execution executes in caller's tenant context and streams result."""
        from packages.ai.service import stream_chat

        user = {"id": 10, "username": "alice", "business_id": 401, "role": "admin"}

        tc = MagicMock()
        tc.index = 0
        tc.id = "call_prod_1"
        tc.function.name = "list_products"
        tc.function.arguments = '{"limit": 10}'

        chunks_1 = [MockChunk(tool_calls=[tc])]
        chunks_2 = [MockChunk(content="Found your products!")]

        observed_tenant = []

        def spy_list_products(*args, **kwargs):
            t = get_current_tenant()
            observed_tenant.append(t)
            return [{"id": 101, "name": "Tenant 401 Widget", "business_id": t}]

        with (
            patch("packages.ai.service.OpenAI") as mock_openai_cls,
            patch.object(inventory_mcp._products_svc, "list", side_effect=spy_list_products),
        ):
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.chat.completions.create.side_effect = [chunks_1, chunks_2]

            events = list(stream_chat([], "list products", user=user))

        assert observed_tenant == [401]

        # Verify emitted events
        event_data = [json.loads(e[6:].strip()) for e in events if e.startswith("data: ")]
        types = [d.get("type") for d in event_data]
        assert "tool_start" in types
        assert "tool_end" in types
        assert "text" in types
        text_content = "".join(d.get("content", "") for d in event_data if d.get("type") == "text")
        assert "Found your products!" in text_content

    def test_ai_chat_cross_tenant_isolation_between_users(self):
        """Verify two AI chat sessions from different tenants receive strictly isolated data."""
        from packages.ai.service import stream_chat

        user_a = {"id": 1, "username": "tenant_a_user", "business_id": 801}
        user_b = {"id": 2, "username": "tenant_b_user", "business_id": 802}

        # Mock function call for list_orders
        tc_a = MagicMock()
        tc_a.index = 0
        tc_a.id = "call_order_a"
        tc_a.function.name = "list_orders"
        tc_a.function.arguments = "{}"

        tc_b = MagicMock()
        tc_b.index = 0
        tc_b.id = "call_order_b"
        tc_b.function.name = "list_orders"
        tc_b.function.arguments = "{}"

        executed_orders_tenant = []

        def spy_list_orders(*args, **kwargs):
            t = get_current_tenant()
            executed_orders_tenant.append(t)
            return [{"id": t, "order_number": f"SO-TENANT-{t}", "business_id": t}]

        with (
            patch("packages.ai.service.OpenAI") as mock_openai_cls,
            patch.object(sales_mcp._orders_svc, "list", side_effect=spy_list_orders),
        ):
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client

            # Session A
            mock_client.chat.completions.create.side_effect = [
                [MockChunk(tool_calls=[tc_a])],
                [MockChunk(content="Here are Tenant A orders.")],
            ]
            events_a = list(stream_chat([], "orders for a", user=user_a))

            # Session B
            mock_client.chat.completions.create.side_effect = [
                [MockChunk(tool_calls=[tc_b])],
                [MockChunk(content="Here are Tenant B orders.")],
            ]
            events_b = list(stream_chat([], "orders for b", user=user_b))

        assert executed_orders_tenant == [801, 802]
        text_a = "".join(json.loads(e[6:].strip()).get("content", "") for e in events_a if e.startswith("data: ") and json.loads(e[6:].strip()).get("type") == "text")
        text_b = "".join(json.loads(e[6:].strip()).get("content", "") for e in events_b if e.startswith("data: ") and json.loads(e[6:].strip()).get("type") == "text")
        assert "Here are Tenant A orders." in text_a
        assert "Here are Tenant B orders." in text_b

    def test_ai_chat_chained_multi_tool_scoping(self):
        """Verify multiple sequential tool calls in an AI chat stream all inherit tenant context."""
        from packages.ai.service import stream_chat

        user = {"id": 99, "username": "super_rep", "business_id": 950}

        # Step 1: list_products
        tc1 = MagicMock()
        tc1.index = 0
        tc1.id = "call_step1"
        tc1.function.name = "list_products"
        tc1.function.arguments = "{}"

        # Step 2: create_order
        tc2 = MagicMock()
        tc2.index = 0
        tc2.id = "call_step2"
        tc2.function.name = "create_order"
        tc2.function.arguments = '{"customer_id": 12}'

        executed_tenants = []

        def spy_list_products(*args, **kwargs):
            executed_tenants.append(("list_products", get_current_tenant()))
            return [{"id": 1, "name": "Item", "business_id": get_current_tenant()}]

        def spy_create_order(payload):
            executed_tenants.append(("create_order", get_current_tenant()))
            return {"id": 100, "customer_id": payload["customer_id"], "business_id": get_current_tenant()}

        with (
            patch("packages.ai.service.OpenAI") as mock_openai_cls,
            patch.object(inventory_mcp._products_svc, "list", side_effect=spy_list_products),
            patch.object(sales_mcp._orders_svc, "create", side_effect=spy_create_order),
        ):
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.chat.completions.create.side_effect = [
                [MockChunk(tool_calls=[tc1])],
                [MockChunk(tool_calls=[tc2])],
                [MockChunk(content="Chained operations completed.")],
            ]

            events = list(stream_chat([], "list then order", user=user))

        assert executed_tenants == [
            ("list_products", 950),
            ("create_order", 950),
        ]
        assert get_current_tenant() is None

    def test_ai_chat_tier2_propose_and_confirm_isolation(self):
        """Verify Tier 2 tools called by AI emit confirmation_required and retain tenant context on confirmation."""
        from packages.ai.service import stream_chat

        user = {"id": 33, "username": "warehouse_lead", "business_id": 612}

        # Tier 2 tool: confirm_order
        tc = MagicMock()
        tc.index = 0
        tc.id = "call_tier2_confirm"
        tc.function.name = "confirm_order"
        tc.function.arguments = '{"id": 404}'

        chunks_1 = [MockChunk(tool_calls=[tc])]
        chunks_2 = [MockChunk(content="Proposal recorded, please confirm.")]

        with patch("packages.ai.service.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.chat.completions.create.side_effect = [chunks_1, chunks_2]

            events = list(stream_chat([], "confirm order 404", user=user))

        conf_events = [json.loads(e[6:].strip()) for e in events if e.startswith("data: ") and "confirmation_required" in e]
        assert len(conf_events) == 1
        action_id = conf_events[0]["action_id"]

        assert action_id in _pending_actions
        assert _pending_actions[action_id]["user"]["business_id"] == 612
        assert _pending_actions[action_id]["tool_name"] == "confirm_order"

        # Now confirm the action and verify execution under Tenant 612
        confirmed_tenants = []

        def spy_update_order(order_id, payload):
            t = get_current_tenant()
            confirmed_tenants.append((order_id, payload.get("status"), t))
            return {"id": order_id, "status": payload.get("status"), "business_id": t}

        with patch.object(sales_mcp._orders_svc, "update", side_effect=spy_update_order):
            res = confirm_action(action_id)
            assert res["status"] == "Confirmed"
            assert res["business_id"] == 612
            assert confirmed_tenants == [(404, "Confirmed", 612)]

    def test_ai_chat_jwt_precedence_over_env_var(self, monkeypatch):
        """Verify authenticated JWT user tenant ID overrides environment variable NOVA_TENANT_ID."""
        from packages.ai.service import stream_chat

        monkeypatch.setenv("NOVA_TENANT_ID", "9999")
        user = {"id": 1, "username": "jwt_user", "business_id": 1234}

        tc = MagicMock()
        tc.index = 0
        tc.id = "call_p"
        tc.function.name = "list_purchase_orders"
        tc.function.arguments = "{}"

        observed_tenant = []

        def spy_list_po(*args, **kwargs):
            observed_tenant.append(get_current_tenant())
            return [{"id": 1, "order_number": "PO-1234", "business_id": get_current_tenant()}]

        with (
            patch("packages.ai.service.OpenAI") as mock_openai_cls,
            patch.object(purchasing_mcp._po_svc, "list", side_effect=spy_list_po),
        ):
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.chat.completions.create.side_effect = [
                [MockChunk(tool_calls=[tc])],
                [MockChunk(content="Done")],
            ]

            list(stream_chat([], "list po", user=user))

        assert observed_tenant == [1234]

    def test_ai_router_http_endpoint_tenant_propagation(self):
        """Verify POST /api/ai/chat HTTP endpoint extracts tenant from JWT and executes tools scoped."""
        test_client = TestClient(main_app)
        token = create_access_token(user_id=88, business_id=777)

        tc = MagicMock()
        tc.index = 0
        tc.id = "call_chat_http"
        tc.function.name = "list_invoices"
        tc.function.arguments = "{}"

        observed_tenant = []

        def spy_list_invoices(*args, **kwargs):
            observed_tenant.append(get_current_tenant())
            return [{"id": 99, "invoice_number": "INV-777", "business_id": 777}]

        with (
            patch("packages.auth.deps.get_user_by_id", return_value={"id": 88, "username": "bill", "role": "admin", "business_id": 777}),
            patch("packages.ai.service.OpenAI") as mock_openai_cls,
            patch.object(accounting_mcp._inv_svc, "list", side_effect=spy_list_invoices),
        ):
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.chat.completions.create.side_effect = [
                [MockChunk(tool_calls=[tc])],
                [MockChunk(content="Here are your invoices.")],
            ]

            resp = test_client.post(
                "/api/ai/chat",
                json={"message": "show my invoices"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        assert "Here are your invoices." in resp.text
        assert observed_tenant == [777]


# ============================================================================
# 4. Cross-Server MCP Domain Multi-Tenant Coverage Tests
# ============================================================================


class TestCrossServerDomainTenantIsolation:
    """Test tenant context propagation across all domain MCP servers."""

    def test_all_15_domain_servers_execute_under_tenant_context(self):
        """Verify calling tools across all 15 MCP servers executes in the specified tenant context."""
        # 1. database_mcp
        database_mcp.register_tools()
        with (
            patch("packages.mcp.servers.database_mcp.get_connection") as mock_get_conn,
            patch("packages.mcp.servers.database_mcp.release_connection"),
        ):
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchmany.return_value = [{"id": 1, "business_id": 99}]
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur
            mock_get_conn.return_value = mock_conn

            res = call_tool("execute_read_query", {"sql": "SELECT * FROM \"Nova\".t0001 WHERE business_id = 99"}, user={"business_id": 99})
            assert len(res) == 1

        # 2. inventory_mcp
        inventory_mcp.register_tools()
        with patch.object(inventory_mcp._products_svc, "list") as mock_svc:
            mock_svc.side_effect = lambda *a, **k: [{"tenant": get_current_tenant()}]
            res = call_tool("list_products", {}, user={"business_id": 10})
            assert res == [{"tenant": 10}]

        # 3. sales_mcp
        sales_mcp.register_tools()
        with patch.object(sales_mcp._orders_svc, "list") as mock_svc:
            mock_svc.side_effect = lambda *a, **k: [{"tenant": get_current_tenant()}]
            res = call_tool("list_orders", {}, user={"business_id": 20})
            assert res == [{"tenant": 20}]

        # 4. purchasing_mcp
        purchasing_mcp.register_tools()
        with patch.object(purchasing_mcp._po_svc, "list") as mock_svc:
            mock_svc.side_effect = lambda *a, **k: [{"tenant": get_current_tenant()}]
            res = call_tool("list_purchase_orders", {}, user={"business_id": 30})
            assert res == [{"tenant": 30}]

        # 5. accounting_mcp
        accounting_mcp.register_tools()
        with patch.object(accounting_mcp._inv_svc, "list") as mock_svc:
            mock_svc.side_effect = lambda *a, **k: [{"tenant": get_current_tenant()}]
            res = call_tool("list_invoices", {}, user={"business_id": 40})
            assert res == [{"tenant": 40}]

        # 6. admin_mcp
        admin_mcp.register_tools()
        with patch.object(admin_mcp._settings_svc, "list") as mock_svc:
            mock_svc.side_effect = lambda *a, **k: [{"tenant": get_current_tenant()}]
            res = call_tool("list_settings", {}, user={"business_id": 50})
            assert res == [{"tenant": 50}]

        # 7. warehouse_mcp
        warehouse_mcp.register_tools()
        with patch.object(warehouse_mcp._gr_svc, "list") as mock_svc:
            mock_svc.side_effect = lambda *a, **k: [{"tenant": get_current_tenant()}]
            res = call_tool("list_goods_receipts", {}, user={"business_id": 60})
            assert res == [{"tenant": 60}]

        # 8. hr_mcp
        hr_mcp.register_tools()
        with patch.object(hr_mcp._emp_svc, "list") as mock_svc:
            mock_svc.side_effect = lambda *a, **k: [{"tenant": get_current_tenant()}]
            res = call_tool("list_employees", {}, user={"business_id": 70})
            assert res == [{"tenant": 70}]

        # 9. bi_mcp
        bi_mcp.register_tools()
        with patch.object(bi_mcp._kpi_def_svc, "list") as mock_svc:
            mock_svc.side_effect = lambda *a, **k: [{"tenant": get_current_tenant()}]
            res = call_tool("list_kpis", {}, user={"business_id": 80})
            assert res == [{"tenant": 80}]

        # 10. crm_mcp
        crm_mcp.register_tools()
        with patch.object(crm_mcp._leads_svc, "list") as mock_svc:
            mock_svc.side_effect = lambda *a, **k: [{"tenant": get_current_tenant()}]
            res = call_tool("list_leads", {}, user={"business_id": 90})
            assert res == [{"tenant": 90}]

        # 11. projects_mcp
        projects_mcp.register_tools()
        with patch.object(projects_mcp._proj_svc, "list") as mock_svc:
            mock_svc.side_effect = lambda *a, **k: [{"tenant": get_current_tenant()}]
            res = call_tool("list_projects", {}, user={"business_id": 110})
            assert res == [{"tenant": 110}]

        # 12. manufacturing_mcp
        manufacturing_mcp.register_tools()
        with patch.object(manufacturing_mcp._mfg_svc, "list") as mock_svc:
            mock_svc.side_effect = lambda *a, **k: [{"tenant": get_current_tenant()}]
            res = call_tool("list_manufacturing_orders", {}, user={"business_id": 120})
            assert res == [{"tenant": 120}]

        # 13. maintenance_mcp
        maintenance_mcp.register_tools()
        with patch.object(maintenance_mcp._asset_svc, "list") as mock_svc:
            mock_svc.side_effect = lambda *a, **k: [{"tenant": get_current_tenant()}]
            res = call_tool("list_assets", {}, user={"business_id": 130})
            assert res == [{"tenant": 130}]

        # 14. notifications_mcp
        notifications_mcp.register_tools()
        with patch.object(notifications_mcp._notif_svc, "list") as mock_svc:
            mock_svc.side_effect = lambda *a, **k: [{"tenant": get_current_tenant()}]
            res = call_tool("list_user_notifications", {"user_id": 1}, user={"business_id": 140})
            assert res == [{"tenant": 140}]

        # 15. pos_mcp
        pos_mcp.register_tools()
        with patch("packages.mcp.servers.pos_mcp.process_pos_checkout") as mock_checkout:
            mock_checkout.side_effect = lambda req: MagicMock(
                model_dump=lambda: {"order_id": 1, "business_id": get_current_tenant()}
            )
            res = call_tool(
                "pos_checkout",
                {"cart_items": [{"product_id": 1, "product_name": "P1", "qty": 1, "unit_price": 10.0}]},
                user={"business_id": 150},
            )
            assert res["business_id"] == 150

    def test_inventory_search_products_sql_tenant_scoping(self):
        """Verify custom raw SQL in _search_products queries with business_id = %s parameter."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            {"id": 1, "name": "Alpha Item", "sku": "A-01", "business_id": 333}
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        with (
            patch("packages.mcp.servers.inventory_mcp.get_connection", return_value=mock_conn),
            patch("packages.mcp.servers.inventory_mcp.release_connection"),
        ):
            inventory_mcp.register_tools()
            res = call_tool("search_products", {"query": "Alpha"}, user={"business_id": 333})

        call_args = mock_cur.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert "business_id = %s" in sql
        assert 333 in params
        assert res[0]["business_id"] == 333
