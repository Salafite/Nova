import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock
import pytest

from packages.security.audit import (
    record_security_event,
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
