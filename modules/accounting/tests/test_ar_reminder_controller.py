"""
Unit and Integration Tests for AR Reminders & Statement Configuration REST Controller.

Tests endpoints:
- GET, POST /api/accounting/reminder-rules
- GET, PUT, DELETE /api/accounting/reminder-rules/{id}
- GET, POST /api/accounting/reminder-templates
- GET, PUT, DELETE /api/accounting/reminder-templates/{id}
- POST /api/accounting/reminders/dispatch
- POST /api/accounting/reminders/dispatch-statement
- POST /api/accounting/reminders/run-batch
- GET, POST /api/accounting/customers/{customer_id}/statement-pdf
- GET /api/accounting/reminders/summary
- POST /api/accounting/reminders/evaluate-eligibility
"""

import io
import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.accounting.controllers.ar_reminder_controller import router, service
from modules.accounting.services.ar_reminder_service import ARReminderService
from modules.accounting.models.reminder import BatchReminderResult


@pytest.fixture
def mock_ar_service():
    """Create a mock ARReminderService with in-memory repositories."""
    svc = MagicMock(spec=ARReminderService)
    svc.customer_repo = MagicMock()
    svc.invoice_repo = MagicMock()
    svc.rule_repo = MagicMock()
    svc.template_repo = MagicMock()
    svc.statement_pdf_service = MagicMock()
    return svc


@pytest.fixture
def client(mock_ar_service):
    """FastAPI TestClient configured with the AR reminders controller and mocked service."""
    app = FastAPI()
    app.include_router(router)

    # Patch the service singleton in controller
    with patch("modules.accounting.controllers.ar_reminder_controller.service", mock_ar_service):
        yield TestClient(app)


# ----------------------------------------------------------------------
# 1. AR Reminder Rules Tests
# ----------------------------------------------------------------------
class TestReminderRulesEndpoints:
    def test_list_reminder_rules(self, client, mock_ar_service):
        mock_ar_service.list_rules.return_value = [
            {
                "id": 1,
                "rule_name": "Overdue 30 Days Reminder",
                "rule_code": "RULE-30D",
                "trigger_type": "AGING_THRESHOLD",
                "threshold_days": 30,
                "channel": "ALL",
                "is_active": True,
                "template_id": 10,
                "template_name": "Standard Overdue Notice",
            }
        ]

        response = client.get("/api/accounting/reminder-rules?is_active=true&trigger_type=AGING_THRESHOLD")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["rule_name"] == "Overdue 30 Days Reminder"
        mock_ar_service.list_rules.assert_called_once_with(
            is_active=True,
            trigger_type="AGING_THRESHOLD",
            channel=None,
            limit=100,
            offset=0,
        )

    def test_create_reminder_rule_success(self, client, mock_ar_service):
        mock_ar_service.create_rule.return_value = {
            "id": 2,
            "rule_name": "Weekly Friday Statements",
            "rule_code": "RULE-FRI-STMT",
            "trigger_type": "STATEMENT_SCHEDULE",
            "schedule_day": "FRIDAY",
            "schedule_time": "09:00:00",
            "channel": "EMAIL",
            "threshold_days": 0,
            "frequency": "WEEKLY",
            "attach_statement_pdf": True,
            "include_payment_link": True,
            "min_overdue_balance": 0.0,
            "exclude_vip": True,
            "exclude_credit_hold": False,
            "is_active": True,
        }

        payload = {
            "rule_name": "Weekly Friday Statements",
            "rule_code": "RULE-FRI-STMT",
            "trigger_type": "STATEMENT_SCHEDULE",
            "schedule_day": "FRIDAY",
            "schedule_time": "09:00:00",
            "channel": "EMAIL",
            "frequency": "WEEKLY",
            "attach_statement_pdf": True,
            "include_payment_link": True,
        }

        response = client.post("/api/accounting/reminder-rules", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 2
        assert data["rule_code"] == "RULE-FRI-STMT"

    def test_get_reminder_rule_by_id(self, client, mock_ar_service):
        mock_ar_service.get_rule.return_value = {
            "id": 1,
            "rule_name": "30 Days Overdue",
            "threshold_days": 30,
        }

        response = client.get("/api/accounting/reminder-rules/1")
        assert response.status_code == 200
        assert response.json()["id"] == 1

        mock_ar_service.get_rule.return_value = None
        response_404 = client.get("/api/accounting/reminder-rules/999")
        assert response_404.status_code == 404

    def test_update_reminder_rule(self, client, mock_ar_service):
        mock_ar_service.get_rule.return_value = {"id": 1, "rule_name": "Old Name"}
        mock_ar_service.update_rule.return_value = {"id": 1, "rule_name": "Updated Name", "threshold_days": 45}

        response = client.put("/api/accounting/reminder-rules/1", json={"rule_name": "Updated Name", "threshold_days": 45})
        assert response.status_code == 200
        assert response.json()["rule_name"] == "Updated Name"

        mock_ar_service.get_rule.return_value = None
        response_404 = client.put("/api/accounting/reminder-rules/999", json={"rule_name": "X"})
        assert response_404.status_code == 404

    def test_delete_reminder_rule(self, client, mock_ar_service):
        mock_ar_service.get_rule.return_value = {"id": 1, "rule_name": "To Delete"}
        mock_ar_service.delete_rule.return_value = True

        response = client.delete("/api/accounting/reminder-rules/1")
        assert response.status_code == 200
        assert response.json()["success"] is True

        mock_ar_service.get_rule.return_value = None
        response_404 = client.delete("/api/accounting/reminder-rules/999")
        assert response_404.status_code == 404


# ----------------------------------------------------------------------
# 2. AR Reminder Templates Tests
# ----------------------------------------------------------------------
class TestReminderTemplatesEndpoints:
    def test_list_reminder_templates(self, client, mock_ar_service):
        mock_ar_service.list_templates.return_value = [
            {
                "id": 10,
                "template_code": "TMPL-EM-DEFAULT",
                "template_name": "Friendly Email Reminder",
                "channel": "EMAIL",
                "subject_template": "Reminder: Invoice Balance",
                "body_template": "Dear {{customer_name}}, please pay {{overdue_amount}}.",
                "is_active": True,
            }
        ]

        response = client.get("/api/accounting/reminder-templates?channel=EMAIL")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["template_name"] == "Friendly Email Reminder"

    def test_create_reminder_template_success(self, client, mock_ar_service):
        mock_ar_service.create_template.return_value = {
            "id": 11,
            "template_code": "TMPL-WA-URGENT",
            "template_name": "Urgent WhatsApp Notice",
            "channel": "WHATSAPP",
            "body_template": "Hello {{customer_name}}, balance: {{total_balance}}",
            "is_active": True,
        }

        payload = {
            "template_name": "Urgent WhatsApp Notice",
            "channel": "WHATSAPP",
            "body_template": "Hello {{customer_name}}, balance: {{total_balance}}",
        }

        response = client.post("/api/accounting/reminder-templates", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 11

    def test_get_reminder_template_by_id(self, client, mock_ar_service):
        mock_ar_service.get_template.return_value = {
            "id": 10,
            "template_name": "Email Template",
        }

        response = client.get("/api/accounting/reminder-templates/10")
        assert response.status_code == 200
        assert response.json()["id"] == 10

        mock_ar_service.get_template.return_value = None
        response_404 = client.get("/api/accounting/reminder-templates/999")
        assert response_404.status_code == 404

    def test_update_reminder_template(self, client, mock_ar_service):
        mock_ar_service.get_template.return_value = {"id": 10, "template_name": "Old"}
        mock_ar_service.update_template.return_value = {"id": 10, "template_name": "New"}

        response = client.put("/api/accounting/reminder-templates/10", json={"template_name": "New"})
        assert response.status_code == 200
        assert response.json()["template_name"] == "New"

        mock_ar_service.get_template.return_value = None
        response_404 = client.put("/api/accounting/reminder-templates/999", json={"template_name": "X"})
        assert response_404.status_code == 404

    def test_delete_reminder_template(self, client, mock_ar_service):
        mock_ar_service.get_template.return_value = {"id": 10, "template_name": "To Delete"}
        mock_ar_service.delete_template.return_value = True

        response = client.delete("/api/accounting/reminder-templates/10")
        assert response.status_code == 200
        assert response.json()["success"] is True

        mock_ar_service.get_template.return_value = None
        response_404 = client.delete("/api/accounting/reminder-templates/999")
        assert response_404.status_code == 404


# ----------------------------------------------------------------------
# 3. Manual Reminder & Statement Dispatch Tests
# ----------------------------------------------------------------------
class TestManualDispatchEndpoints:
    def test_dispatch_manual_reminder_success(self, client, mock_ar_service):
        mock_ar_service.send_customer_reminder.return_value = {
            "success": True,
            "customer_id": 101,
            "customer_name": "Gourmet Bistro",
            "results": {
                "EMAIL": {"status": "SENT", "message_id": "msg-123"},
            },
        }

        payload = {
            "customer_id": 101,
            "rule_id": 1,
            "channel": "EMAIL",
            "custom_message": "Please settle today",
            "attach_statement_pdf": True,
            "include_payment_link": True,
        }

        response = client.post("/api/accounting/reminders/dispatch", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["customer_id"] == 101

    def test_dispatch_manual_reminder_customer_not_found(self, client, mock_ar_service):
        mock_ar_service.send_customer_reminder.side_effect = ValueError("Customer #999 was not found.")

        payload = {
            "customer_id": 999,
            "channel": "EMAIL",
        }

        response = client.post("/api/accounting/reminders/dispatch", json=payload)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_dispatch_customer_statement_success(self, client, mock_ar_service):
        mock_ar_service.dispatch_customer_statement.return_value = {
            "success": True,
            "customer_id": 101,
            "channel": "EMAIL",
            "results": {
                "EMAIL": {"status": "SENT", "message_id": "stmt-msg-456"},
            },
        }

        payload = {
            "customer_id": 101,
            "channel": "EMAIL",
            "custom_message": "Monthly Account Statement",
        }

        response = client.post("/api/accounting/reminders/dispatch-statement", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Test alias route /api/accounting/statements/dispatch
        alias_response = client.post("/api/accounting/statements/dispatch", json=payload)
        assert alias_response.status_code == 200

    def test_dispatch_customer_statement_customer_not_found(self, client, mock_ar_service):
        mock_ar_service.dispatch_customer_statement.side_effect = ValueError("Customer #999 was not found.")

        payload = {
            "customer_id": 999,
            "channel": "EMAIL",
        }

        response = client.post("/api/accounting/reminders/dispatch-statement", json=payload)
        assert response.status_code == 404


# ----------------------------------------------------------------------
# 4. Batch Reminder Engine Tests
# ----------------------------------------------------------------------
class TestBatchReminderEngineEndpoints:
    def test_run_batch_reminders_dry_run(self, client, mock_ar_service):
        mock_ar_service.run_batch_reminders.return_value = BatchReminderResult(
            total_evaluated=5,
            total_eligible=2,
            total_dispatched=2,
            total_skipped_vip=1,
            total_skipped_excluded=1,
            total_skipped_balance=1,
            dispatched_communications=[
                {
                    "customer_id": 101,
                    "customer_name": "Customer A",
                    "channel": "EMAIL",
                    "overdue_amount": 1200.0,
                    "dry_run": True,
                    "status": "PREVIEW",
                }
            ],
        )

        payload = {
            "dry_run": True,
            "force": False,
        }

        response = client.post("/api/accounting/reminders/run-batch", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["total_evaluated"] == 5
        assert data["total_eligible"] == 2
        assert len(data["dispatched_communications"]) == 1
        assert data["dispatched_communications"][0]["dry_run"] is True

    def test_run_batch_reminders_live(self, client, mock_ar_service):
        mock_ar_service.run_batch_reminders.return_value = BatchReminderResult(
            total_evaluated=3,
            total_eligible=1,
            total_dispatched=1,
            total_failed=0,
            dispatched_communications=[
                {
                    "customer_id": 101,
                    "customer_name": "Customer A",
                    "status": "SENT",
                }
            ],
        )

        payload = {
            "rule_id": 1,
            "customer_ids": [101, 102],
            "dry_run": False,
        }

        response = client.post("/api/accounting/reminders/run-batch", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["total_dispatched"] == 1


# ----------------------------------------------------------------------
# 5. Customer Statement PDF Streaming Tests
# ----------------------------------------------------------------------
class TestStatementPdfStreamingEndpoints:
    def test_get_customer_statement_pdf_success(self, client, mock_ar_service):
        mock_ar_service.customer_repo.get.return_value = {
            "id": 101,
            "name": "Gourmet Bistro",
        }
        fake_pdf_bytes = b"%PDF-1.4 sample statement pdf content bytes"
        mock_ar_service.statement_pdf_service.generate_statement_pdf_for_customer.return_value = fake_pdf_bytes

        response = client.get("/api/accounting/customers/101/statement-pdf?as_of_date=2026-09-08")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "statement_customer_101" in response.headers["content-disposition"]
        assert response.content == fake_pdf_bytes

    def test_get_customer_statement_pdf_customer_not_found(self, client, mock_ar_service):
        mock_ar_service.customer_repo.get.return_value = None

        response = client.get("/api/accounting/customers/999/statement-pdf")
        assert response.status_code == 404
        assert "999" in response.json()["detail"]

    def test_post_customer_statement_pdf(self, client, mock_ar_service):
        mock_ar_service.customer_repo.get.return_value = {
            "id": 101,
            "name": "Gourmet Bistro",
        }
        fake_pdf_bytes = b"%PDF-1.4 post test pdf bytes"
        mock_ar_service.statement_pdf_service.generate_statement_pdf_for_customer.return_value = fake_pdf_bytes

        payload = {
            "as_of_date": "2026-09-08",
            "custom_message": "Special audit note",
            "currency": "USD",
        }

        response = client.post("/api/accounting/customers/101/statement-pdf", json=payload)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == fake_pdf_bytes


# ----------------------------------------------------------------------
# 6. AR Summary & Eligibility Evaluation Tests
# ----------------------------------------------------------------------
class TestSummaryAndEligibilityEndpoints:
    def test_get_ar_reminders_summary(self, client, mock_ar_service):
        mock_ar_service.get_ar_overdue_summary.return_value = {
            "as_of_date": "2026-09-08",
            "total_customers": 50,
            "overdue_customers_count": 12,
            "vip_customers_count": 5,
            "excluded_customers_count": 2,
            "total_balance": 150000.0,
            "total_overdue": 45000.0,
            "current_balance": 105000.0,
            "aging_breakdown": {
                "current": 105000.0,
                "1_30": 20000.0,
                "31_60": 15000.0,
                "61_90": 7000.0,
                "90_plus": 3000.0,
            },
        }

        response = client.get("/api/accounting/reminders/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_customers"] == 50
        assert data["total_overdue"] == 45000.0
        assert data["aging_breakdown"]["90_plus"] == 3000.0

    def test_evaluate_customer_eligibility_eligible(self, client, mock_ar_service):
        mock_ar_service.customer_repo.get.return_value = {"id": 101, "name": "Bistro"}
        mock_ar_service.get_rule.return_value = {"id": 1, "rule_name": "Rule 30D"}
        mock_ar_service.evaluate_customer_eligibility.return_value = {
            "eligible": True,
            "reason": "ELIGIBLE",
            "customer_id": 101,
            "total_balance": 5400.0,
            "overdue_amount": 3200.0,
            "target_channel": "EMAIL",
        }

        payload = {
            "customer_id": 101,
            "rule_id": 1,
            "as_of_date": "2026-09-08",
        }

        response = client.post("/api/accounting/reminders/evaluate-eligibility", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["eligible"] is True
        assert data["reason"] == "ELIGIBLE"

    def test_evaluate_customer_eligibility_customer_not_found(self, client, mock_ar_service):
        mock_ar_service.customer_repo.get.return_value = None
        mock_ar_service.get_rule.return_value = {"id": 1, "rule_name": "Rule 30D"}

        response = client.post(
            "/api/accounting/reminders/evaluate-eligibility",
            json={"customer_id": 999, "rule_id": 1},
        )
        assert response.status_code == 404

    def test_evaluate_customer_eligibility_rule_not_found(self, client, mock_ar_service):
        mock_ar_service.customer_repo.get.return_value = {"id": 101, "name": "Bistro"}
        mock_ar_service.get_rule.return_value = None

        response = client.post(
            "/api/accounting/reminders/evaluate-eligibility",
            json={"customer_id": 101, "rule_id": 999},
        )
        assert response.status_code == 404
