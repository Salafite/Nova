import json
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock
from pydantic import BaseModel

from packages.mcp.types import Tool, UserContext
from packages.mcp.registry import (
    register_tool,
    call_tool,
    propose_action,
    confirm_action,
    _tools,
    _resources,
    _pending_actions,
)
from packages.redis.client import get_redis_client
from modules.core.context import tenant_context, clear_current_tenant
from packages.ai.service import stream_chat


class SampleModel(BaseModel):
    name: str
    amount: Decimal


class TestMcpAuditLogging:
    def setup_method(self):
        _tools.clear()
        _resources.clear()
        _pending_actions.clear()
        clear_current_tenant()
        try:
            get_redis_client().flushdb()
        except Exception:
            pass

    def teardown_method(self):
        clear_current_tenant()

    def test_tool_call_successful_execution_creates_audit_log(self):
        """Successful tool invocation creates a T0023 audit record with MCP_SUCCESS."""
        tool = Tool(
            name="get_product_details",
            description="Get product details",
            input_schema={"type": "object", "properties": {"id": {"type": "integer"}}},
            required_permission="PRODUCTS_VIEW",
        )
        register_tool(tool, lambda id: {"id": id, "name": "Industrial Valve", "price": 120.5})

        user = {"id": 15, "username": "sales_user", "role": "Sales Rep", "business_id": 4}

        with patch("packages.security.audit._audit_repo.create") as mock_create:
            mock_create.return_value = {"id": 501}

            result = call_tool("get_product_details", {"id": 102}, user=user)

            assert result == {"id": 102, "name": "Industrial Valve", "price": 120.5}
            assert mock_create.called
            call_payload, kwargs = mock_create.call_args
            entry = call_payload[0]

            assert entry["table_name"] == "MCP_TOOL"
            assert entry["record_id"] == 102
            assert entry["action"] == "MCP_SUCCESS"
            assert entry["changed_by"] == 15
            assert entry["business_id"] == 4
            assert kwargs.get("business_id") == 4

            data = json.loads(entry["changed_data"])
            assert data["event"] == "mcp_tool_execution"
            assert data["tool_name"] == "get_product_details"
            assert data["arguments"] == {"id": 102}
            assert data["status"] == "SUCCESS"
            assert data["user_id"] == 15
            assert data["role"] == "Sales Rep"
            assert data["tenant_id"] == 4
            assert data["required_permission"] == "PRODUCTS_VIEW"
            assert data["result"] == {"id": 102, "name": "Industrial Valve", "price": 120.5}
            assert "latency_ms" in data

    def test_tool_call_permission_denial_creates_audit_log(self):
        """Permission denied tool execution creates a T0023 audit record with MCP_DENIED."""
        tool = Tool(
            name="purge_records",
            description="Purge records",
            input_schema={},
            required_permission="ADMIN_VIEW",
        )
        register_tool(tool, lambda: "purged")

        user = {"id": 22, "username": "viewer", "role": "Viewer", "business_id": 2}

        with patch("packages.security.audit._audit_repo.create") as mock_create:
            mock_create.return_value = {"id": 502}

            with pytest.raises(PermissionError, match="ADMIN_VIEW required"):
                call_tool("purge_records", {}, user=user)

            assert mock_create.called
            call_payload, kwargs = mock_create.call_args
            entry = call_payload[0]

            assert entry["table_name"] == "MCP_TOOL"
            assert entry["action"] == "MCP_DENIED"
            assert entry["changed_by"] == 22
            assert entry["business_id"] == 2

            data = json.loads(entry["changed_data"])
            assert data["event"] == "mcp_tool_execution"
            assert data["tool_name"] == "purge_records"
            assert data["status"] == "DENIED"
            assert data["user_id"] == 22
            assert data["role"] == "Viewer"
            assert data["tenant_id"] == 2
            assert data["required_permission"] == "ADMIN_VIEW"
            assert "Permission denied" in data["error"]

    def test_tool_call_exception_creates_audit_log(self):
        """Tool handler raising an unhandled exception logs MCP_ERROR in T0023."""
        def faulty_handler(order_id: int):
            raise RuntimeError("Database connection timeout")

        tool = Tool(
            name="process_order",
            description="Process order",
            input_schema={"type": "object", "properties": {"order_id": {"type": "integer"}}},
            required_permission="SALES_VIEW",
        )
        register_tool(tool, faulty_handler)

        user = {"id": 33, "username": "rep", "role": "Sales Rep", "business_id": 1}

        with patch("packages.security.audit._audit_repo.create") as mock_create:
            mock_create.return_value = {"id": 503}

            with pytest.raises(RuntimeError, match="Database connection timeout"):
                call_tool("process_order", {"order_id": 77}, user=user)

            assert mock_create.called
            call_payload, kwargs = mock_create.call_args
            entry = call_payload[0]

            assert entry["table_name"] == "MCP_TOOL"
            assert entry["action"] == "MCP_ERROR"
            assert entry["changed_by"] == 33
            assert entry["business_id"] == 1

            data = json.loads(entry["changed_data"])
            assert data["event"] == "mcp_tool_execution"
            assert data["tool_name"] == "process_order"
            assert data["status"] == "ERROR"
            assert data["error"] == "Database connection timeout"

    def test_tool_not_found_creates_audit_log(self):
        """Calling an unregistered tool logs MCP_ERROR in T0023."""
        user = {"id": 5, "username": "admin", "role": "Admin", "business_id": 1}

        with patch("packages.security.audit._audit_repo.create") as mock_create:
            mock_create.return_value = {"id": 504}

            with pytest.raises(ValueError, match="Tool not found: unknown_tool"):
                call_tool("unknown_tool", {"foo": "bar"}, user=user)

            assert mock_create.called
            call_payload, kwargs = mock_create.call_args
            entry = call_payload[0]

            assert entry["table_name"] == "MCP_TOOL"
            assert entry["action"] == "MCP_ERROR"
            assert entry["changed_by"] == 5

            data = json.loads(entry["changed_data"])
            assert data["tool_name"] == "unknown_tool"
            assert data["status"] == "ERROR"
            assert "Tool not found" in data["error"]

    def test_complex_parameter_and_result_serialization(self):
        """Audit logging serializes complex objects (datetime, Decimal, Pydantic, bytes) safely."""
        tool = Tool(
            name="compute_metrics",
            description="Compute metrics",
            input_schema={},
            required_permission="BI_VIEW",
        )
        now = datetime.now(timezone.utc)
        register_tool(
            tool,
            lambda: {
                "timestamp": now,
                "revenue": Decimal("987654.32"),
                "raw_buffer": b"raw_data_stream",
                "model": SampleModel(name="Quarterly Report", amount=Decimal("1234.56")),
            }
        )

        user = {"id": 8, "username": "mgr", "role": "Manager", "business_id": 3}

        with patch("packages.security.audit._audit_repo.create") as mock_create:
            mock_create.return_value = {"id": 505}

            result = call_tool("compute_metrics", {}, user=user)

            assert mock_create.called
            call_payload, _ = mock_create.call_args
            entry = call_payload[0]

            data = json.loads(entry["changed_data"])
            assert data["status"] == "SUCCESS"
            assert data["result"]["timestamp"] == now.isoformat()
            assert data["result"]["revenue"] == 987654.32
            assert data["result"]["raw_buffer"] == "raw_data_stream"
            assert data["result"]["model"] == {"name": "Quarterly Report", "amount": 1234.56}

    def test_propose_action_successful_creates_audit_log(self):
        """propose_action generates an MCP_PROPOSE record in T0023."""
        tool = Tool(
            name="cancel_order",
            description="Cancel order",
            input_schema={"type": "object", "properties": {"id": {"type": "integer"}}},
            tier="tier2",
            required_permission="SALES_VIEW",
        )
        register_tool(tool, lambda id: f"cancelled {id}")

        user = {"id": 12, "role": "Sales Rep", "business_id": 5}

        with patch("packages.security.audit._audit_repo.create") as mock_create:
            mock_create.return_value = {"id": 601}

            proposal = propose_action("cancel_order", {"id": 88}, user=user)

            assert proposal["tool"] == "cancel_order"
            assert mock_create.called
            call_payload, kwargs = mock_create.call_args
            entry = call_payload[0]

            assert entry["table_name"] == "MCP_ACTION"
            assert entry["record_id"] == 88
            assert entry["action"] == "MCP_PROPOSE"
            assert entry["changed_by"] == 12
            assert entry["business_id"] == 5

            data = json.loads(entry["changed_data"])
            assert data["event"] == "mcp_propose_confirm"
            assert data["action_type"] == "PROPOSE"
            assert data["action_id"] == proposal["action_id"]
            assert data["tool_name"] == "cancel_order"
            assert data["arguments"] == {"id": 88}
            assert data["status"] == "SUCCESS"

    def test_propose_action_denied_creates_audit_log(self):
        """propose_action with unauthorized user logs MCP_PROPOSE denial to T0023."""
        tool = Tool(
            name="delete_product",
            description="Delete product",
            input_schema={"type": "object", "properties": {"id": {"type": "integer"}}},
            tier="tier2",
            required_permission="PRODUCTS_VIEW",
        )
        register_tool(tool, lambda id: f"deleted {id}")

        user = {"id": 99, "role": "Customer", "business_id": 1}

        with patch("packages.security.audit._audit_repo.create") as mock_create:
            mock_create.return_value = {"id": 602}

            with pytest.raises(PermissionError, match="PRODUCTS_VIEW required"):
                propose_action("delete_product", {"id": 55}, user=user)

            assert mock_create.called
            call_payload, _ = mock_create.call_args
            entry = call_payload[0]

            assert entry["table_name"] == "MCP_ACTION"
            assert entry["action"] == "MCP_PROPOSE"
            assert entry["changed_by"] == 99

            data = json.loads(entry["changed_data"])
            assert data["status"] == "DENIED"
            assert "Permission denied" in data["error"]

    def test_confirm_action_creates_propose_and_confirm_audit_logs(self):
        """Complete Tier 2 flow creates PROPOSE, TOOL SUCCESS, and CONFIRM audit entries."""
        tool = Tool(
            name="convert_quotation_to_order",
            description="Convert quotation",
            input_schema={"type": "object", "properties": {"id": {"type": "integer"}}},
            tier="tier2",
            required_permission="SALES_VIEW",
        )
        register_tool(tool, lambda id: {"order_id": 9901, "quotation_id": id})

        user = {"id": 4, "role": "Sales Rep", "business_id": 2}

        with patch("packages.security.audit._audit_repo.create") as mock_create:
            mock_create.side_effect = [{"id": 701}, {"id": 702}, {"id": 703}]

            proposal = propose_action("convert_quotation_to_order", {"id": 450}, user=user)
            action_id = proposal["action_id"]

            result = confirm_action(action_id, user=user)

            assert result == {"order_id": 9901, "quotation_id": 450}
            assert mock_create.call_count >= 3

            # Check PROPOSE entry
            prop_entry = mock_create.call_args_list[0][0][0]
            assert prop_entry["action"] == "MCP_PROPOSE"

            # Check underlying TOOL EXECUTION entry
            tool_entry = mock_create.call_args_list[1][0][0]
            assert tool_entry["action"] == "MCP_SUCCESS"
            assert tool_entry["table_name"] == "MCP_TOOL"

            # Check CONFIRM entry
            conf_entry = mock_create.call_args_list[2][0][0]
            assert conf_entry["action"] == "MCP_CONFIRM"
            assert conf_entry["table_name"] == "MCP_ACTION"
            conf_data = json.loads(conf_entry["changed_data"])
            assert conf_data["action_type"] == "CONFIRM"
            assert conf_data["action_id"] == action_id
            assert conf_data["status"] == "SUCCESS"
            assert conf_data["result"] == {"order_id": 9901, "quotation_id": 450}

    def test_confirm_action_expired_creates_error_audit_log(self):
        """confirm_action with non-existent / expired action_id logs MCP_CONFIRM error."""
        user = {"id": 10, "role": "Manager", "business_id": 1}

        with patch("packages.security.audit._audit_repo.create") as mock_create:
            mock_create.return_value = {"id": 801}

            with pytest.raises(ValueError, match="Action not found or expired"):
                confirm_action("non-existent-action-uuid", user=user)

            assert mock_create.called
            call_payload, _ = mock_create.call_args
            entry = call_payload[0]

            assert entry["table_name"] == "MCP_ACTION"
            assert entry["action"] == "MCP_CONFIRM"
            assert entry["changed_by"] == 10

            data = json.loads(entry["changed_data"])
            assert data["status"] == "ERROR"
            assert "Action not found or expired" in data["error"]

    def test_multi_tenant_isolation_in_audit_records(self):
        """Audit logging properly respects tenant_context and user-provided tenant IDs."""
        tool = Tool(
            name="list_inventory",
            description="List inventory",
            input_schema={},
            required_permission="INVENTORY_VIEW",
        )
        register_tool(tool, lambda: ["itemA", "itemB"])

        # Test with UserContext object
        user_obj = UserContext(id=77, username="inv_mgr", role="Manager", business_id=19, permissions=["INVENTORY_VIEW"])

        with patch("packages.security.audit._audit_repo.create") as mock_create:
            mock_create.return_value = {"id": 901}

            call_tool("list_inventory", {}, user=user_obj)

            call_payload, kwargs = mock_create.call_args
            entry = call_payload[0]
            assert entry["business_id"] == 19
            assert kwargs.get("business_id") == 19
            data = json.loads(entry["changed_data"])
            assert data["tenant_id"] == 19
            assert data["user_id"] == 77

    def test_ai_service_stream_chat_triggers_audit_logging(self):
        """stream_chat tool executions are captured in security audit logs."""
        tool = Tool(
            name="check_stock",
            description="Check stock",
            input_schema={"type": "object", "properties": {"sku": {"type": "string"}}},
            required_permission="INVENTORY_VIEW",
        )
        register_tool(tool, lambda sku: {"sku": sku, "stock": 450})

        user = {"id": 88, "username": "ai_user", "role": "Manager", "business_id": 6}

        # Mock OpenAI streaming chunks
        mock_chunk_1 = MagicMock()
        mock_delta_1 = MagicMock()
        mock_delta_1.content = None
        mock_tc = MagicMock()
        mock_tc.index = 0
        mock_tc.id = "call_abc123"
        mock_tc.function.name = "check_stock"
        mock_tc.function.arguments = json.dumps({"sku": "SKU-900"})
        mock_delta_1.tool_calls = [mock_tc]
        mock_chunk_1.choices = [MagicMock(delta=mock_delta_1)]

        mock_chunk_2 = MagicMock()
        mock_delta_2 = MagicMock()
        mock_delta_2.content = "The stock for SKU-900 is 450."
        mock_delta_2.tool_calls = None
        mock_chunk_2.choices = [MagicMock(delta=mock_delta_2)]

        with patch("packages.ai.service.os.getenv") as mock_env:
            mock_env.side_effect = lambda k, default=None: "sk-mock-key" if k == "OPENAI_API_KEY" else default
            with patch("packages.ai.service.OpenAI") as mock_openai_cls:
                mock_client = MagicMock()
                mock_openai_cls.return_value = mock_client
                mock_client.chat.completions.create.side_effect = [
                    [mock_chunk_1],
                    [mock_chunk_2],
                ]

                with patch("packages.security.audit._audit_repo.create") as mock_create:
                    mock_create.return_value = {"id": 1001}

                    events = list(stream_chat([], "Check stock for SKU-900", user=user))

                    assert len(events) > 0
                    assert mock_create.called
                    call_payload, kwargs = mock_create.call_args
                    entry = call_payload[0]

                    assert entry["table_name"] == "MCP_TOOL"
                    assert entry["action"] == "MCP_SUCCESS"
                    assert entry["changed_by"] == 88
                    assert entry["business_id"] == 6

                    data = json.loads(entry["changed_data"])
                    assert data["tool_name"] == "check_stock"
                    assert data["arguments"] == {"sku": "SKU-900"}
                    assert data["status"] == "SUCCESS"
                    assert data["result"] == {"sku": "SKU-900", "stock": 450}
