import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from modules.purchasing.controllers.T0081I import router, service
from packages.auth.deps import get_current_user


@pytest.fixture
def auth_user():
    return {
        "id": 42,
        "username": "qa_supervisor",
        "role": "Supervisor",
        "business_id": 1,
        "permissions": ["PURCHASING_VIEW", "PURCHASING_MANAGE", "PURCHASING_ALL"],
    }


@pytest.fixture
def app(auth_user):
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_current_user] = lambda: auth_user
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestT0081IRMAApprovalEndpoints:
    def test_approve_purchase_return_success(self, client):
        mock_response = {
            "id": 10,
            "return_number": "RMA-202609-0010",
            "status": "Approved",
            "supplier_id": 5,
            "total_amount": 250.0,
            "debit_memo_id": 99,
            "approved_at": "2026-09-08T09:30:00",
            "approved_by": 42,
            "notes": "Approved for vendor pickup",
        }
        with patch.object(service, "approve_return", return_value=mock_response) as mock_approve:
            payload = {
                "approved_by": 42,
                "notes": "Approved for vendor pickup",
                "create_debit_memo": True,
                "quarantine_inventory": True,
            }
            resp = client.post("/api/T0081I/10/approve", json=payload)
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["id"] == 10
            assert data["status"] == "Approved"
            assert data["debit_memo_id"] == 99
            assert data["approved_by"] == 42
            assert data["total_amount"] == 250.0

            mock_approve.assert_called_once_with(
                id_val=10,
                approved_by=42,
                notes="Approved for vendor pickup",
                create_debit_memo=True,
                quarantine_inventory=True,
            )

    def test_approve_purchase_return_empty_body_defaults_user(self, client):
        mock_response = {
            "id": 11,
            "return_number": "RMA-202609-0011",
            "status": "Approved",
            "approved_by": 42,
            "debit_memo_id": 100,
        }
        with patch.object(service, "approve_return", return_value=mock_response) as mock_approve:
            resp = client.post("/api/T0081I/11/approve")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["status"] == "Approved"
            assert data["approved_by"] == 42
            mock_approve.assert_called_once_with(
                id_val=11,
                approved_by=42,
                notes=None,
                create_debit_memo=True,
                quarantine_inventory=True,
            )

    def test_approve_purchase_return_not_found_returns_404(self, client):
        with patch.object(service, "approve_return", side_effect=HTTPException(status_code=404, detail="Purchase Return #999 not found")):
            resp = client.post("/api/T0081I/999/approve")
            assert resp.status_code == status.HTTP_404_NOT_FOUND
            assert "Purchase Return #999 not found" in resp.json()["detail"]

    def test_approve_purchase_return_validation_error_returns_400(self, client):
        with patch.object(service, "approve_return", side_effect=ValueError("Cannot approve return with no line items")):
            resp = client.post("/api/T0081I/12/approve")
            assert resp.status_code == status.HTTP_400_BAD_REQUEST
            assert "no line items" in resp.json()["detail"].lower()

    def test_approve_purchase_return_internal_error_returns_500(self, client):
        with patch.object(service, "approve_return", side_effect=RuntimeError("Database lock failure")):
            resp = client.post("/api/T0081I/13/approve")
            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to approve RMA" in resp.json()["detail"]


class TestT0081IDockRejectionEndpoints:
    def test_create_rma_from_goods_receipt_with_payload(self, client):
        mock_response = {
            "id": 20,
            "return_number": "RMA-202609-0020",
            "goods_receipt_id": 105,
            "purchase_order_id": 50,
            "supplier_id": 8,
            "status": "Draft",
            "total_amount": 300.0,
            "reason": "Damaged goods upon arrival",
            "lines": [
                {
                    "id": 1,
                    "return_id": 20,
                    "product_id": 201,
                    "product_name": "Organic Milk",
                    "qty": 20.0,
                    "unit_price": 15.0,
                    "line_total": 300.0,
                    "reason_code": "damaged",
                    "quarantine_status": "Quarantine",
                }
            ],
        }
        rejection_payload = {
            "goods_receipt_id": 105,
            "purchase_order_id": 50,
            "supplier_id": 8,
            "reason": "Damaged goods upon arrival",
            "lines": [
                {
                    "product_id": 201,
                    "product_name": "Organic Milk",
                    "qty_rejected": 20.0,
                    "unit_price": 15.0,
                    "reason_code": "damaged",
                    "reason_details": "Broken seal",
                }
            ],
        }
        with patch.object(service, "create_from_goods_receipt", return_value=mock_response) as mock_create:
            resp = client.post("/api/T0081I/from-goods-receipt/105", json=rejection_payload)
            assert resp.status_code == status.HTTP_201_CREATED
            data = resp.json()
            assert data["id"] == 20
            assert data["goods_receipt_id"] == 105
            assert data["total_amount"] == 300.0
            assert len(data["lines"]) == 1
            mock_create.assert_called_once()
            args = mock_create.call_args[1]
            assert args["grn_id"] == 105
            assert args["rejection_payload"]["supplier_id"] == 8

    def test_create_rma_from_goods_receipt_without_body(self, client):
        mock_response = {
            "id": 21,
            "return_number": "RMA-202609-0021",
            "goods_receipt_id": 106,
            "supplier_id": 9,
            "status": "Draft",
            "lines": [],
        }
        with patch.object(service, "create_from_goods_receipt", return_value=mock_response) as mock_create:
            resp = client.post("/api/T0081I/from-goods-receipt/106")
            assert resp.status_code == status.HTTP_201_CREATED
            data = resp.json()
            assert data["id"] == 21
            assert data["goods_receipt_id"] == 106
            mock_create.assert_called_once_with(grn_id=106, rejection_payload={"business_id": 1})

    def test_create_rma_from_goods_receipt_not_found(self, client):
        with patch.object(service, "create_from_goods_receipt", side_effect=HTTPException(status_code=404, detail="Goods Receipt #999 not found")):
            resp = client.post("/api/T0081I/from-goods-receipt/999")
            assert resp.status_code == status.HTTP_404_NOT_FOUND
            assert "Goods Receipt #999 not found" in resp.json()["detail"]

    def test_create_rma_from_goods_receipt_value_error(self, client):
        with patch.object(service, "create_from_goods_receipt", side_effect=ValueError("Supplier ID is required")):
            resp = client.post("/api/T0081I/from-goods-receipt/107")
            assert resp.status_code == status.HTTP_400_BAD_REQUEST
            assert "supplier id is required" in resp.json()["detail"].lower()

    def test_create_rma_from_dock_rejection_endpoint(self, client):
        mock_response = {
            "id": 22,
            "return_number": "RMA-202609-0022",
            "goods_receipt_id": 110,
            "supplier_id": 12,
            "status": "Draft",
            "total_amount": 120.0,
        }
        payload = {
            "goods_receipt_id": 110,
            "supplier_id": 12,
            "reason": "Expired batches on dock",
            "lines": [
                {
                    "product_id": 305,
                    "product_name": "Greek Yogurt",
                    "qty_rejected": 10.0,
                    "unit_price": 12.0,
                    "reason_code": "expired",
                }
            ],
        }
        with patch.object(service, "create_dock_rejection", return_value=mock_response) as mock_dock:
            resp = client.post("/api/T0081I/dock-rejection", json=payload)
            assert resp.status_code == status.HTTP_201_CREATED
            data = resp.json()
            assert data["id"] == 22
            assert data["total_amount"] == 120.0
            mock_dock.assert_called_once()

    def test_create_dock_rejection_missing_lines_validation_error(self, client):
        invalid_payload = {
            "goods_receipt_id": 110,
            "supplier_id": 12,
            "lines": [],
        }
        resp = client.post("/api/T0081I/dock-rejection", json=invalid_payload)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestT0081IAttachmentEndpoints:
    def test_upload_return_attachment_to_header_success(self, client):
        mock_attachment_response = {
            "id": "att-12345",
            "filename": "damage_proof.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 1024,
            "data_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
            "uploaded_by": 42,
        }
        with patch.object(service, "add_attachment", return_value=mock_attachment_response) as mock_add:
            payload = {
                "filename": "damage_proof.jpg",
                "content_type": "image/jpeg",
                "data_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
                "description": "Crushed boxes during delivery",
            }
            resp = client.post("/api/T0081I/10/attachments", json=payload)
            assert resp.status_code == status.HTTP_201_CREATED
            data = resp.json()
            assert data["id"] == "att-12345"
            assert data["filename"] == "damage_proof.jpg"
            assert data["size_bytes"] == 1024
            mock_add.assert_called_once()

    def test_upload_return_attachment_to_line_item(self, client):
        mock_attachment_response = {
            "id": "att-line-99",
            "filename": "line_damage.png",
            "url": "https://cdn.example.com/line_damage.png",
            "line_id": 5,
        }
        with patch.object(service, "add_attachment", return_value=mock_attachment_response) as mock_add:
            payload = {
                "filename": "line_damage.png",
                "url": "https://cdn.example.com/line_damage.png",
                "line_id": 5,
            }
            resp = client.post("/api/T0081I/10/attachments", json=payload)
            assert resp.status_code == status.HTTP_201_CREATED
            data = resp.json()
            assert data["id"] == "att-line-99"
            assert data["line_id"] == 5

    def test_upload_attachment_return_not_found(self, client):
        with patch.object(service, "add_attachment", side_effect=HTTPException(status_code=404, detail="Purchase Return #999 not found")):
            payload = {"filename": "img.png", "url": "https://example.com/img.png"}
            resp = client.post("/api/T0081I/999/attachments", json=payload)
            assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_return_attachments_endpoint(self, client):
        mock_attachments = [
            {"id": "att-1", "filename": "dock_sheet.pdf", "line_id": None},
            {"id": "att-2", "filename": "cracked_box.jpg", "line_id": 10},
        ]
        with patch.object(service, "get_attachments", return_value=mock_attachments) as mock_get:
            resp = client.get("/api/T0081I/15/attachments")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert len(data) == 2
            assert data[0]["id"] == "att-1"
            assert data[1]["id"] == "att-2"
            mock_get.assert_called_once_with(return_id=15)

    def test_get_return_attachments_not_found(self, client):
        with patch.object(service, "get_attachments", side_effect=HTTPException(status_code=404, detail="Purchase Return #999 not found")):
            resp = client.get("/api/T0081I/999/attachments")
            assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_return_attachment_endpoint(self, client):
        with patch.object(service, "delete_attachment", return_value={"ok": True, "attachment_id": "att-1"}) as mock_del:
            resp = client.delete("/api/T0081I/15/attachments/att-1?line_id=10")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["ok"] is True
            mock_del.assert_called_once_with(return_id=15, attachment_id="att-1", line_id=10)

    def test_delete_return_attachment_error(self, client):
        with patch.object(service, "delete_attachment", side_effect=ValueError("Attachment not found")):
            resp = client.delete("/api/T0081I/15/attachments/invalid-att")
            assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestT0081IDetailsAndSlipDataEndpoints:
    def test_get_purchase_return_details_endpoint(self, client):
        mock_details = {
            "id": 30,
            "return_number": "RMA-202609-0030",
            "return_date": "2026-09-08",
            "status": "Approved",
            "supplier_id": 14,
            "supplier_name": "Organic Dairy Co",
            "purchase_order_id": 22,
            "po_number": "PO-2026-0022",
            "goods_receipt_id": 45,
            "grn_number": "GRN-2026-0045",
            "debit_memo_id": 88,
            "debit_memo_number": "DM-2026-0088",
            "total_amount": 500.0,
            "reason": "Spoiled goods on delivery",
            "lines": [
                {
                    "id": 101,
                    "return_id": 30,
                    "product_id": 1001,
                    "product_name": "Organic Milk 1L",
                    "qty": 50.0,
                    "unit_price": 10.0,
                    "line_total": 500.0,
                    "batch_number": "LOT-MILK-99",
                    "reason_code": "expired",
                    "quarantine_status": "Quarantine",
                    "disposition": "Return to Vendor",
                    "line_number": 1,
                }
            ],
            "attachments": [],
        }
        with patch.object(service, "get_return_details", return_value=mock_details) as mock_get_details:
            resp = client.get("/api/T0081I/30/details")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["id"] == 30
            assert data["supplier_name"] == "Organic Dairy Co"
            assert data["po_number"] == "PO-2026-0022"
            assert data["debit_memo_number"] == "DM-2026-0088"
            assert data["total_amount"] == 500.0
            assert len(data["lines"]) == 1
            mock_get_details.assert_called_once_with(return_id=30)

    def test_get_purchase_return_details_not_found(self, client):
        with patch.object(service, "get_return_details", side_effect=ValueError("Purchase Return #999 not found")):
            resp = client.get("/api/T0081I/999/details")
            assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_purchase_return_slip_data_endpoint(self, client):
        mock_slip = {
            "return_id": 30,
            "return_number": "RMA-202609-0030",
            "return_date": "2026-09-08",
            "status": "Approved",
            "company_name": "Nova ERP Hub",
            "supplier_id": 14,
            "supplier_name": "Organic Dairy Co",
            "supplier_code": "SUP-0014",
            "po_number": "PO-2026-0022",
            "grn_number": "GRN-2026-0045",
            "debit_memo_id": 88,
            "debit_memo_number": "DM-2026-0088",
            "total_amount": 500.0,
            "currency": "USD",
            "lines": [
                {
                    "id": 101,
                    "product_name": "Organic Milk 1L",
                    "qty": 50.0,
                    "uom": "EA",
                    "unit_price": 10.0,
                    "line_total": 500.0,
                    "batch_number": "LOT-MILK-99",
                    "reason_code": "expired",
                    "reason_label": "Expired Product",
                    "quarantine_status": "Quarantine",
                    "disposition": "Return to Vendor",
                    "photos": [],
                }
            ],
            "attachments": [],
            "acknowledgment_text": "Supplier acknowledgment verifies debit memo claims.",
        }
        with patch.object(service, "get_return_slip_data", return_value=mock_slip) as mock_slip_data:
            resp = client.get("/api/T0081I/30/slip-data")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["return_id"] == 30
            assert data["supplier_name"] == "Organic Dairy Co"
            assert data["debit_memo_number"] == "DM-2026-0088"
            assert data["total_amount"] == 500.0
            assert data["lines"][0]["reason_label"] == "Expired Product"
            assert "acknowledgment_text" in data
            mock_slip_data.assert_called_once_with(return_id=30)

    def test_get_purchase_return_slip_data_not_found(self, client):
        with patch.object(service, "get_return_slip_data", side_effect=ValueError("Purchase Return #999 not found")):
            resp = client.get("/api/T0081I/999/slip-data")
            assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestT0081ILifecycleTransitions:
    def test_complete_purchase_return_endpoint(self, client):
        mock_response = {
            "id": 40,
            "return_number": "RMA-202609-0040",
            "status": "Returned",
            "notes": "Truck loaded and departed facility",
        }
        with patch.object(service, "complete_return", return_value=mock_response) as mock_complete:
            resp = client.post("/api/T0081I/40/complete-return", json={"notes": "Truck loaded and departed facility"})
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["id"] == 40
            assert data["status"] == "Returned"
            mock_complete.assert_called_once_with(id_val=40, notes="Truck loaded and departed facility")

    def test_complete_purchase_return_invalid_status_error(self, client):
        with patch.object(service, "complete_return", side_effect=HTTPException(status_code=400, detail="Cannot complete return in Draft status")):
            resp = client.post("/api/T0081I/41/complete-return")
            assert resp.status_code == status.HTTP_400_BAD_REQUEST
            assert "Cannot complete return" in resp.json()["detail"]

    def test_cancel_purchase_return_endpoint(self, client):
        mock_response = {
            "id": 42,
            "return_number": "RMA-202609-0042",
            "status": "Cancelled",
            "notes": "Cancelled by supplier agreement",
        }
        with patch.object(service, "cancel_return", return_value=mock_response) as mock_cancel:
            resp = client.post("/api/T0081I/42/cancel", json={"reason": "Cancelled by supplier agreement"})
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["id"] == 42
            assert data["status"] == "Cancelled"
            mock_cancel.assert_called_once_with(id_val=42, reason="Cancelled by supplier agreement")

    def test_cancel_purchase_return_terminal_error(self, client):
        with patch.object(service, "cancel_return", side_effect=HTTPException(status_code=400, detail="Cannot cancel a completed return")):
            resp = client.post("/api/T0081I/43/cancel")
            assert resp.status_code == status.HTTP_400_BAD_REQUEST
            assert "Cannot cancel" in resp.json()["detail"]


class TestT0081ICrudRoutes:
    def test_list_returns_endpoint(self, client):
        mock_list = [
            {
                "id": 1,
                "return_number": "RMA-202609-0001",
                "supplier_id": 5,
                "status": "Draft",
                "total_amount": 100.0,
                "return_date": "2026-09-08",
            }
        ]
        with patch.object(service, "list", return_value=mock_list) as mock_svc_list, \
             patch.object(service, "count", return_value=1):
            resp = client.get("/api/T0081I/")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert len(data) == 1
            assert data[0]["return_number"] == "RMA-202609-0001"
            assert resp.headers.get("X-Total-Count") == "1"

    def test_get_return_by_id_endpoint(self, client):
        mock_record = {
            "id": 1,
            "return_number": "RMA-202609-0001",
            "supplier_id": 5,
            "status": "Draft",
            "total_amount": 100.0,
            "return_date": "2026-09-08",
        }
        with patch.object(service, "get", return_value=mock_record):
            resp = client.get("/api/T0081I/1")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["id"] == 1
            assert data["return_number"] == "RMA-202609-0001"

    def test_create_return_endpoint(self, client):
        mock_created = {
            "id": 2,
            "return_number": "RMA-202609-0002",
            "supplier_id": 6,
            "status": "Draft",
            "total_amount": 0.0,
            "return_date": "2026-09-08",
        }
        payload = {
            "supplier_id": 6,
            "reason": "Test return creation",
        }
        with patch.object(service, "create", return_value=mock_created), \
             patch("modules.core.controllers.base.CrudRepository.create", return_value=True):
            resp = client.post("/api/T0081I/", json=payload)
            assert resp.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
            data = resp.json()
            assert data["id"] == 2
            assert data["supplier_id"] == 6

    def test_delete_return_endpoint(self, client):
        mock_record = {
            "id": 2,
            "return_number": "RMA-202609-0002",
            "supplier_id": 6,
            "status": "Draft",
        }
        with patch.object(service, "get", return_value=mock_record), \
             patch.object(service, "delete", return_value=True), \
             patch("modules.core.controllers.base.CrudRepository.create", return_value=True):
            resp = client.delete("/api/T0081I/2")
            assert resp.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]
