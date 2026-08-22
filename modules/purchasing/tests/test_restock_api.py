from unittest.mock import patch, MagicMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.purchasing.controllers import restock_controller
from modules.purchasing.services.restock_agent import RestockAgentService
from modules.administration.services.scheduler_service import SchedulerService
from modules.administration.services.notification_service import NotificationService
from packages.auth.deps import require_permission, get_current_user



app = FastAPI()
app.dependency_overrides[get_current_user] = lambda: {
    "id": 1,
    "username": "admin",
    "role": "Admin",
    "permissions": ["*"],
}
app.include_router(restock_controller.router)
client = TestClient(app)


MOCK_PRODUCT = {"id": 101, "name": "Organic Whole Milk", "sku": "MILK-001", "cost_price": 3.0}
MOCK_FORECAST = {
    "product_id": 101,
    "product_name": "Organic Whole Milk",
    "sku": "MILK-001",
    "needs_restock": True,
    "urgency": "CRITICAL",
    "available_stock": 10.0,
    "velocity_30d": 5.0,
    "days_of_inventory": 2.0,
    "projected_stockout_date": "2026-08-25",
    "lead_time_days": 5,
    "min_order_qty": 50.0,
    "suggested_order_qty": 100.0,
    "unit_cost": 2.5,
    "estimated_cost": 250.0,
    "supplier_id": 2,
    "supplier_name": "Dairy Farm Co",
    "rationale": "[CRITICAL RESTOCK] MILK-001: 2 days supply remaining.",
}


class TestRestockAPI:
    def test_get_restock_suggestions(self):
        with patch.object(restock_controller._forecast_svc, "calculate_all_forecasts", return_value=[MOCK_FORECAST]):
            resp = client.get("/api/purchasing/restock/suggestions?days=30&only_at_risk=true")
            assert resp.status_code == 200
            data = resp.json()
            assert "summary" in data
            assert "suggestions" in data
            assert data["summary"]["at_risk_count"] == 1
            assert data["summary"]["critical_count"] == 1
            assert data["summary"]["total_estimated_spend"] == 250.0
            assert len(data["suggestions"]) == 1
            assert data["suggestions"][0]["sku"] == "MILK-001"

    def test_approve_restock_suggestion(self):
        with patch.object(restock_controller._product_repo, "get", return_value=MOCK_PRODUCT), \
             patch.object(restock_controller._forecast_svc, "calculate_sku_forecast", return_value=MOCK_FORECAST), \
             patch.object(restock_controller._po_repo, "list", return_value=[]), \
             patch.object(restock_controller._po_svc, "create", return_value={"id": 15, "order_number": "PO-001", "status": "Pending", "total": 250.0}), \
             patch.object(restock_controller._po_line_repo, "create", return_value={"id": 1, "purchase_order_id": 15, "qty": 100.0}):
            
            resp = client.post("/api/purchasing/restock/suggestions/101/approve")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert data["purchase_order"]["order_number"] == "PO-001"
            assert data["purchase_order"]["status"] == "Pending"
            assert len(data["lines"]) == 1

    def test_edit_restock_suggestion(self):
        with patch.object(restock_controller._product_repo, "get", return_value=MOCK_PRODUCT), \
             patch.object(restock_controller._forecast_svc, "calculate_sku_forecast", return_value=MOCK_FORECAST), \
             patch.object(restock_controller._po_repo, "list", return_value=[]), \
             patch.object(restock_controller._po_svc, "create", return_value={"id": 16, "order_number": "PO-002", "status": "Pending", "total": 550.0}), \
             patch.object(restock_controller._po_line_repo, "create", return_value={"id": 2, "purchase_order_id": 16, "qty": 100.0}):

            payload = {
                "qty": 100,
                "supplier_id": 3,
                "unit_price": 5.5,
                "expected_date": "2026-09-01",
                "notes": "Customized procurement order",
            }
            resp = client.post("/api/purchasing/restock/suggestions/101/edit", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert data["purchase_order"]["order_number"] == "PO-002"

    def test_reject_restock_suggestion(self):
        with patch.object(restock_controller._product_repo, "get", return_value=MOCK_PRODUCT):
            payload = {"reason": "Overstocked at secondary facility"}
            resp = client.post("/api/purchasing/restock/suggestions/101/reject", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert data["status"] == "Dismissed"
            assert data["product_id"] == 101

    def test_run_forecast_endpoint(self):
        mock_eval_result = {
            "status": "success",
            "total_skus_evaluated": 50,
            "at_risk_count": 3,
            "critical_count": 1,
            "recommendations": [MOCK_FORECAST],
        }
        with patch.object(restock_controller._restock_agent, "run_evaluation", return_value=mock_eval_result):
            resp = client.post("/api/purchasing/restock/run-forecast", json={"days": 30})
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert data["at_risk_count"] == 3

    def test_morning_digest_notification_dispatch(self):
        mock_forecast_svc = MagicMock()
        mock_forecast_svc.calculate_all_forecasts.return_value = [MOCK_FORECAST]
        
        mock_notif_svc = MagicMock()
        mock_notif_svc.notify_roles.return_value = [{"id": 1, "title": "Digest", "user_id": 1}]

        agent = RestockAgentService(
            forecast_service=mock_forecast_svc,
            notification_service=mock_notif_svc,
        )

        result = agent.run_evaluation(send_notification=True)
        assert result["status"] == "success"
        assert result["at_risk_count"] == 1
        assert result["critical_count"] == 1
        assert result["notifications_sent"] == 1
        assert "AI Restock Morning Digest" in result["digest_title"]

        mock_notif_svc.notify_roles.assert_called_once()
        call_kwargs = mock_notif_svc.notify_roles.call_args[1]
        assert call_kwargs["notification_type"] == "Restock"
        assert call_kwargs["reference_type"] == "restock_digest"
        assert "Top Restock Requisitions" in call_kwargs["message"]

    def test_scheduler_service_restock_task_execution(self):
        mock_repo = MagicMock()
        mock_repo.get.return_value = {
            "id": 1,
            "task_name": "Daily Restock Digest",
            "task_type": "DemandForecastRestock",
            "config": {"days": 30, "safety_margin_days": 7, "target_coverage_days": 30},
            "status": "Idle",
        }
        scheduler = SchedulerService(repo=mock_repo)

        with patch("modules.purchasing.services.restock_agent.RestockAgentService.run_evaluation", return_value={"status": "success"}) as mock_run:
            res = scheduler.run_now(1)
            assert res is True
            assert mock_repo.update.call_count >= 2
            # Verify status was updated to Completed
            last_update = mock_repo.update.call_args_list[-1][0]
            assert last_update[0] == 1
            assert last_update[1]["status"] == "Completed"
            mock_run.assert_called_once()
