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

    def test_get_supplier_draft_po_queue(self):
        mock_queue = [
            {
                "supplier_id": 2,
                "supplier_name": "Dairy Farm Co",
                "lead_time_days": 7,
                "expected_date": "2026-08-27",
                "total_items": 2,
                "total_qty": 140.0,
                "total_estimated_cost": 450.0,
                "max_urgency": "CRITICAL",
                "items": [
                    {"product_id": 101, "product_name": "Whole Milk", "sku": "MILK-001", "suggested_order_qty": 100.0, "unit_cost": 2.5, "estimated_cost": 250.0},
                    {"product_id": 102, "product_name": "Cheddar Cheese", "sku": "CHEESE-001", "suggested_order_qty": 40.0, "unit_cost": 5.0, "estimated_cost": 200.0},
                ],
                "po_notes": "Consolidated Draft PO for Dairy Farm Co",
            }
        ]
        with patch.object(restock_controller._forecast_svc, "get_aggregated_supplier_draft_pos", return_value=mock_queue):
            resp = client.get("/api/purchasing/restock/supplier-queue?only_at_risk=true")
            assert resp.status_code == 200
            data = resp.json()
            assert "summary" in data
            assert "supplier_queue" in data
            assert data["summary"]["total_suppliers"] == 1
            assert data["summary"]["total_items"] == 2
            assert data["summary"]["total_estimated_spend"] == 450.0
            assert data["supplier_queue"][0]["supplier_name"] == "Dairy Farm Co"

            # Also check alias route /draft-po-queue
            alias_resp = client.get("/api/purchasing/restock/draft-po-queue")
            assert alias_resp.status_code == 200

    def test_approve_supplier_draft_po(self):
        mock_queue = [
            {
                "supplier_id": 2,
                "supplier_name": "Dairy Farm Co",
                "lead_time_days": 5,
                "expected_date": "2026-08-25",
                "total_items": 1,
                "total_qty": 100.0,
                "total_estimated_cost": 250.0,
                "max_urgency": "CRITICAL",
                "items": [
                    {"product_id": 101, "product_name": "Whole Milk", "suggested_order_qty": 100.0, "unit_cost": 2.5, "estimated_cost": 250.0},
                ],
                "po_notes": "Consolidated PO for Dairy Farm Co",
            }
        ]
        with patch.object(restock_controller._forecast_svc, "get_aggregated_supplier_draft_pos", return_value=mock_queue), \
             patch.object(restock_controller._po_repo, "list", return_value=[]), \
             patch.object(restock_controller._po_svc, "create", return_value={"id": 20, "order_number": "PO-010", "supplier_id": 2, "status": "Pending", "total": 250.0}), \
             patch.object(restock_controller._po_line_repo, "create", return_value={"id": 1, "purchase_order_id": 20, "product_id": 101, "qty": 100.0}):

            resp = client.post("/api/purchasing/restock/supplier-queue/2/approve")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert data["purchase_order"]["order_number"] == "PO-010"
            assert data["total_items"] == 1
            assert data["total_amount"] == 250.0

    def test_approve_supplier_draft_po_with_item_overrides(self):
        with patch.object(restock_controller._product_repo, "get", return_value=MOCK_PRODUCT), \
             patch.object(restock_controller._po_repo, "list", return_value=[]), \
             patch.object(restock_controller._po_svc, "create", return_value={"id": 21, "order_number": "PO-011", "supplier_id": 2, "status": "Pending", "total": 300.0}), \
             patch.object(restock_controller._po_line_repo, "create", return_value={"id": 2, "purchase_order_id": 21, "product_id": 101, "qty": 120.0}):

            payload = {
                "supplier_id": 2,
                "expected_date": "2026-09-05",
                "notes": "Custom multi-item PO override",
                "items": [
                    {"product_id": 101, "qty": 120.0, "unit_price": 2.5, "product_name": "Organic Whole Milk (Bulk)"}
                ]
            }
            resp = client.post("/api/purchasing/restock/supplier-queue/approve", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert data["purchase_order"]["order_number"] == "PO-011"
            assert data["total_amount"] == 300.0

    def test_batch_approve_all_supplier_pos(self):
        mock_queue = [
            {
                "supplier_id": 2,
                "supplier_name": "Dairy Farm Co",
                "lead_time_days": 5,
                "items": [{"product_id": 101, "product_name": "Milk", "suggested_order_qty": 50.0, "unit_cost": 2.0}],
            }
        ]
        with patch.object(restock_controller._forecast_svc, "get_aggregated_supplier_draft_pos", return_value=mock_queue), \
             patch.object(restock_controller, "approve_supplier_draft_po", return_value={"purchase_order": {"id": 25, "order_number": "PO-020"}, "total_amount": 100.0}):

            resp = client.post("/api/purchasing/restock/supplier-queue/approve-all")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert data["total_pos"] == 1
            assert data["total_spend"] == 100.0

    def test_list_supplier_lead_times(self):
        mock_products = [{"id": 101, "name": "Whole Milk", "sku": "MILK-001", "is_active": True}]
        mock_supplier_mapping = {
            "mapping_id": 1,
            "product_id": 101,
            "supplier_id": 2,
            "supplier_name": "Dairy Farm Co",
            "supplier_sku": "DF-MILK-1",
            "unit_cost": 2.5,
            "lead_time_days": 5,
            "min_order_qty": 50.0,
            "is_preferred": True,
        }
        with patch.object(restock_controller._product_repo, "list", return_value=mock_products), \
             patch.object(restock_controller._forecast_svc, "get_preferred_supplier", return_value=mock_supplier_mapping):

            resp = client.get("/api/purchasing/restock/supplier-lead-times")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_mappings"] == 1
            assert len(data["supplier_lead_times"]) == 1
            assert data["supplier_lead_times"][0]["supplier_name"] == "Dairy Farm Co"
            assert data["supplier_lead_times"][0]["lead_time_days"] == 5

    def test_approve_supplier_draft_po_not_found_returns_404(self):
        with patch.object(restock_controller._forecast_svc, "get_aggregated_supplier_draft_pos", return_value=[]):
            resp = client.post("/api/purchasing/restock/supplier-queue/999/approve")
            assert resp.status_code == 404
            assert "No restock items found for supplier #999" in resp.json()["detail"]

    def test_approve_supplier_draft_po_zero_items_returns_400(self):
        payload = {
            "supplier_id": 2,
            "items": []
        }
        resp = client.post("/api/purchasing/restock/supplier-queue/2/approve", json=payload)
        assert resp.status_code == 400
        assert "Cannot create purchase order with zero line items" in resp.json()["detail"]

    def test_batch_approve_all_supplier_pos_empty_queue(self):
        with patch.object(restock_controller._forecast_svc, "get_aggregated_supplier_draft_pos", return_value=[]):
            resp = client.post("/api/purchasing/restock/supplier-queue/approve-all")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert data["total_pos"] == 0
            assert data["total_spend"] == 0.0
            assert "No at-risk supplier queues found" in data["message"]

    def test_approve_restock_suggestion_product_not_found(self):
        with patch.object(restock_controller._product_repo, "get", return_value=None):
            resp = client.post("/api/purchasing/restock/suggestions/999/approve")
            assert resp.status_code == 404
            assert "Product #999 not found" in resp.json()["detail"]

    def test_edit_restock_suggestion_product_not_found(self):
        with patch.object(restock_controller._product_repo, "get", return_value=None):
            payload = {"qty": 50, "unit_price": 4.0}
            resp = client.post("/api/purchasing/restock/suggestions/999/edit", json=payload)
            assert resp.status_code == 404
            assert "Product #999 not found" in resp.json()["detail"]


