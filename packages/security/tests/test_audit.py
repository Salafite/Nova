import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock
import pytest

from packages.security.audit import (
    record_security_event,
    record_mcp_tool_execution,
    record_mcp_propose_confirm,
    log_security_event,
    log_cross_tenant_access,
    record_cross_tenant_attempt,
    _json_safe,
)
from modules.core.context import tenant_context, clear_current_tenant


class TestSecurityAudit:
    def setup_method(self):
        clear_current_tenant()

    def teardown_method(self):
        clear_current_tenant()

    def test_record_security_event_success(self):
        with patch("packages.security.audit._audit_repo.create") as mock_create:
            mock_create.return_value = {"id": 100, "table_name": "T0001", "action": "CROSS_TENANT_ACCESS"}

            result = record_security_event(
                table_name="T0001",
                record_id=42,
                action="CROSS_TENANT_ACCESS",
                user_id=5,
                business_id=1,
                target_tenant_id=2,
                details={"ip": "127.0.0.1", "action": "read"},
            )

            assert result is not None
            assert result["id"] == 100
            assert mock_create.called
            call_payload, kwargs = mock_create.call_args
            entry = call_payload[0]
            assert entry["table_name"] == "T0001"
            assert entry["record_id"] == 42
            assert entry["action"] == "CROSS_TENANT_ACCESS"
            assert entry["changed_by"] == 5
            assert entry["business_id"] == 1
            assert kwargs.get("business_id") == 1

            parsed_data = json.loads(entry["changed_data"])
            assert parsed_data["event"] == "security_audit"
            assert parsed_data["tenant_id"] == 1
            assert parsed_data["target_tenant_id"] == 2
            assert parsed_data["details"] == {"ip": "127.0.0.1", "action": "read"}

    def test_record_security_event_uses_active_tenant_context(self):
        with tenant_context(77):
            with patch("packages.security.audit._audit_repo.create") as mock_create:
                mock_create.return_value = {"id": 101}

                result = record_security_event(
                    table_name="T0010",
                    record_id=99,
                    user_id=12,
                )

                assert result == {"id": 101}
                call_payload, kwargs = mock_create.call_args
                entry = call_payload[0]
                assert entry["business_id"] == 77
                assert kwargs.get("business_id") == 77

                parsed_data = json.loads(entry["changed_data"])
                assert parsed_data["tenant_id"] == 77

    def test_record_security_event_db_failure_handled_gracefully(self, caplog):
        with patch("packages.security.audit._audit_repo.create", side_effect=Exception("DB connection failure")):
            with caplog.at_level(logging.ERROR, logger="security.audit"):
                result = record_security_event(
                    table_name="T0001",
                    record_id=1,
                    user_id=1,
                )
                assert result is None
                assert "Failed to persist security audit event" in caplog.text

    def test_record_security_event_logger_output(self, caplog):
        with patch("packages.security.audit._audit_repo.create", return_value={"id": 1}):
            with caplog.at_level(logging.WARNING, logger="security.audit"):
                record_security_event(
                    table_name="T0012",
                    record_id=55,
                    action="UNAUTHORIZED_ACCESS",
                    user_id=9,
                    business_id=3,
                    target_tenant_id=4,
                    details={"resource": "order"},
                )
                assert "Security event [UNAUTHORIZED_ACCESS] on T0012 id=55" in caplog.text

    def test_json_safe_helper(self):
        now = datetime.now(timezone.utc)
        assert _json_safe(now) == now.isoformat()
        assert _json_safe(Decimal("123.45")) == 123.45
        assert _json_safe(b"test-bytes") == "test-bytes"

        class DummyModel:
            def model_dump(self):
                return {"k": "v"}

        assert _json_safe(DummyModel()) == {"k": "v"}

        with pytest.raises(TypeError):
            _json_safe(object())

    def test_aliases(self):
        with patch("packages.security.audit.record_security_event") as mock_record:
            log_security_event("T0001", 1)
            assert mock_record.called

        with patch("packages.security.audit.record_security_event") as mock_record:
            log_cross_tenant_access("T0001", 1)
            assert mock_record.called

        with patch("packages.security.audit.record_security_event") as mock_record:
            record_cross_tenant_attempt("T0001", 1)
            assert mock_record.called

    def test_record_mcp_tool_execution_success(self):
        with patch("packages.security.audit._audit_repo.create") as mock_create:
            mock_create.return_value = {"id": 200, "table_name": "MCP_TOOL", "action": "MCP_SUCCESS"}

            result = record_mcp_tool_execution(
                tool_name="list_products",
                arguments={"limit": 10},
                result=[{"id": 1, "name": "Widget"}],
                status="SUCCESS",
                user_id=10,
                business_id=2,
                role="Manager",
                required_permission="PRODUCT_READ",
                latency_ms=45.2,
            )

            assert result is not None
            assert result["id"] == 200
            assert mock_create.called
            call_payload, kwargs = mock_create.call_args
            entry = call_payload[0]
            assert entry["table_name"] == "MCP_TOOL"
            assert entry["action"] == "MCP_SUCCESS"
            assert entry["changed_by"] == 10
            assert entry["business_id"] == 2
            assert kwargs.get("business_id") == 2

            parsed = json.loads(entry["changed_data"])
            assert parsed["event"] == "mcp_tool_execution"
            assert parsed["tool_name"] == "list_products"
            assert parsed["arguments"] == {"limit": 10}
            assert parsed["status"] == "SUCCESS"
            assert parsed["user_id"] == 10
            assert parsed["role"] == "Manager"
            assert parsed["tenant_id"] == 2
            assert parsed["required_permission"] == "PRODUCT_READ"
            assert parsed["latency_ms"] == 45.2

    def test_record_mcp_tool_execution_denied_and_error(self, caplog):
        with patch("packages.security.audit._audit_repo.create", return_value={"id": 201}):
            with caplog.at_level(logging.WARNING, logger="security.audit"):
                res = record_mcp_tool_execution(
                    tool_name="delete_product",
                    arguments={"id": 99},
                    status="DENIED",
                    user_id=5,
                    business_id=1,
                    role="Viewer",
                    required_permission="PRODUCT_DELETE",
                    error="Permission denied: PRODUCT_DELETE required",
                )
                assert res == {"id": 201}
                assert "MCP tool [delete_product] DENIED" in caplog.text

        with patch("packages.security.audit._audit_repo.create", return_value={"id": 202}):
            with caplog.at_level(logging.ERROR, logger="security.audit"):
                res = record_mcp_tool_execution(
                    tool_name="execute_read_query",
                    arguments={"query": "SELECT 1"},
                    status="ERROR",
                    user_id=5,
                    business_id=1,
                    role="Admin",
                    error="Syntax error in SQL",
                )
                assert res == {"id": 202}
                assert "MCP tool [execute_read_query] ERROR" in caplog.text

    def test_record_mcp_propose_confirm(self, caplog):
        with patch("packages.security.audit._audit_repo.create") as mock_create:
            mock_create.return_value = {"id": 300}

            result = record_mcp_propose_confirm(
                action_type="PROPOSE",
                tool_name="delete_product",
                action_id="act-12345",
                arguments={"id": 42},
                preview="Delete product 42",
                status="SUCCESS",
                user_id=7,
                business_id=3,
                role="Manager",
            )

            assert result == {"id": 300}
            call_payload, kwargs = mock_create.call_args
            entry = call_payload[0]
            assert entry["table_name"] == "MCP_ACTION"
            assert entry["record_id"] == 42
            assert entry["action"] == "MCP_PROPOSE"
            assert entry["changed_by"] == 7
            assert entry["business_id"] == 3

            parsed = json.loads(entry["changed_data"])
            assert parsed["event"] == "mcp_propose_confirm"
            assert parsed["action_type"] == "PROPOSE"
            assert parsed["action_id"] == "act-12345"
            assert parsed["tool_name"] == "delete_product"
            assert parsed["arguments"] == {"id": 42}
            assert parsed["preview"] == "Delete product 42"

