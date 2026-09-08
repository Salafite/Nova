from unittest.mock import MagicMock, patch
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from modules.purchasing.controllers.T0081I import router, service
from packages.auth.deps import get_current_user, require_permission


@pytest.fixture
def auth_user():
    return {
        "id": 10,
        "username": "receiving_supervisor",
        "role": "Supervisor",
        "business_id": 1,
        "permissions": ["PURCHASING_VIEW", "PURCHASING_ALL", "PURCHASING_MANAGE"],
    }


@pytest.fixture
def app(auth_user):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[require_permission("PURCHASING_VIEW")] = lambda: auth_user
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_approve_purchase_return_endpoint(client):
    with patch.object(service, "approve_return") as mock_approve:
        mock_approve.return_value = {
            "id": 1,
            "return_number": "RMA-00001",
            "status": "Approved",
            "approved_by": 10,
            "total_amount": 350.0,
            "debit_memo_id": 99,
        }

        response = client.post(
            "/api/T0081I/1/approve",
            json={
                "notes": "Approved by supervisor",
                "create_debit_memo": True,
                "quarantine_inventory": True,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["status"] == "Approved"
        mock_approve.assert_called_once()


def test_complete_purchase_return_endpoint(client):
    with patch.object(service, "complete_return") as mock_complete:
        mock_complete.return_value = {
            "id": 1,
            "return_number": "RMA-00001",
            "status": "Returned",
        }

        response = client.post(
            "/api/T0081I/1/complete-return",
            json={"notes": "Vendor driver picked up goods"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "Returned"
        mock_complete.assert_called_once()


def test_from_goods_receipt_endpoint(client):
    with patch.object(service, "create_from_goods_receipt") as mock_from_grn:
        mock_from_grn.return_value = {
            "id": 5,
            "return_number": "RMA-00005",
            "goods_receipt_id": 101,
            "supplier_id": 3,
            "status": "Draft",
            "lines": [
                {
                    "id": 10,
                    "return_id": 5,
                    "product_id": 1,
                    "product_name": "Perishable Milk",
                    "qty": 5.0,
                }
            ],
        }

        payload = {
            "goods_receipt_id": 101,
            "supplier_id": 3,
            "reason": "Dock rejection - damaged cartons",
            "lines": [
                {
                    "product_id": 1,
                    "product_name": "Perishable Milk",
                    "qty_rejected": 5.0,
                    "reason_code": "damaged",
                }
            ],
        }

        response = client.post("/api/T0081I/from-goods-receipt/101", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == 5
        assert data["goods_receipt_id"] == 101
        mock_from_grn.assert_called_once()


def test_get_return_slip_data_endpoint(client):
    with patch.object(service, "get_return_slip_data") as mock_slip:
        mock_slip.return_value = {
            "return_id": 1,
            "return_number": "RMA-00001",
            "supplier_name": "Fresh Dairy Co",
            "debit_memo_number": "DM-00042",
            "total_amount": 500.0,
            "lines": [],
            "acknowledgment_text": "Received the returned merchandise listed above in the condition stated.",
        }

        response = client.get("/api/T0081I/1/slip-data")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["return_id"] == 1
        assert data["supplier_name"] == "Fresh Dairy Co"
        assert "acknowledgment_text" in data
        mock_slip.assert_called_once_with(return_id=1)


def test_get_return_details_endpoint(client):
    with patch.object(service, "get_return_details") as mock_details:
        mock_details.return_value = {
            "id": 1,
            "return_number": "RMA-00001",
            "supplier_name": "Fresh Dairy Co",
            "lines": [
                {
                    "id": 10,
                    "return_id": 1,
                    "product_name": "Perishable Milk",
                    "qty": 5.0,
                }
            ],
        }

        response = client.get("/api/T0081I/1/details")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert len(data["lines"]) == 1
        mock_details.assert_called_once_with(return_id=1)
