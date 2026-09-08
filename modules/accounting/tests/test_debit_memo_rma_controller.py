import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from modules.accounting.controllers.T0090I import router, service
from packages.auth.deps import get_current_user, require_permission


@pytest.fixture
def auth_user():
    return {
        "id": 1,
        "username": "ap_clerk",
        "role": "Accountant",
        "business_id": 1,
        "permissions": ["FINANCE_VIEW", "FINANCE_ALL", "FINANCE_MANAGE"],
    }


@pytest.fixture
def app(auth_user):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[require_permission("FINANCE_VIEW")] = lambda: auth_user
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestInvoiceServiceDebitMemos:
    def setup_method(self):
        self.mock_repo = MagicMock()
        self.service = service
        self._original_repo = self.service.repo
        self.service.repo = self.mock_repo

    def teardown_method(self):
        self.service.repo = self._original_repo

    def test_get_debit_memos_default_filter(self):
        self.mock_repo.list.return_value = [
            {
                "id": 10,
                "invoice_number": "DM-00001",
                "invoice_type": "Debit Memo",
                "partner_id": 5,
                "purchase_return_id": 2,
                "total_amount": 250.0,
                "status": "Unpaid",
            }
        ]

        result = self.service.get_debit_memos()
        assert len(result) == 1
        assert result[0]["invoice_number"] == "DM-00001"
        self.mock_repo.list.assert_called_once_with(
            filters={"invoice_type": "Debit Memo"},
            limit=50,
            offset=0,
            order_by=None,
        )

    def test_get_debit_memos_with_rma_and_supplier_filters(self):
        self.mock_repo.list.return_value = [
            {
                "id": 12,
                "invoice_number": "DM-00002",
                "invoice_type": "Debit Memo",
                "partner_id": 8,
                "purchase_return_id": 4,
                "total_amount": 500.0,
                "status": "Approved",
            }
        ]

        result = self.service.get_debit_memos(
            purchase_return_id=4,
            partner_id=8,
            status="Approved",
            limit=10,
            offset=5,
            order_by="id DESC",
        )
        assert len(result) == 1
        assert result[0]["purchase_return_id"] == 4
        self.mock_repo.list.assert_called_once_with(
            filters={
                "invoice_type": "Debit Memo",
                "purchase_return_id": 4,
                "partner_id": 8,
                "status": "Approved",
            },
            limit=10,
            offset=5,
            order_by="id DESC",
        )

    def test_count_debit_memos(self):
        self.mock_repo.count.return_value = 7
        count = self.service.count_debit_memos(purchase_return_id=3)
        assert count == 7
        self.mock_repo.count.assert_called_once_with(
            filters={"invoice_type": "Debit Memo", "purchase_return_id": 3},
        )

    def test_get_debit_memo_by_purchase_return_found(self):
        self.mock_repo.list.return_value = [
            {
                "id": 15,
                "invoice_number": "DM-00015",
                "invoice_type": "Debit Memo",
                "partner_id": 3,
                "purchase_return_id": 9,
                "total_amount": 120.0,
                "status": "Unpaid",
            }
        ]
        result = self.service.get_debit_memo_by_purchase_return(9)
        assert result is not None
        assert result["id"] == 15
        assert result["purchase_return_id"] == 9

    def test_get_debit_memo_by_purchase_return_not_found(self):
        self.mock_repo.list.return_value = []
        result = self.service.get_debit_memo_by_purchase_return(999)
        assert result is None


class TestT0090IDebitMemoEndpoints:
    def test_list_debit_memos_endpoint(self, client):
        sample_memos = [
            {
                "id": 1,
                "invoice_number": "DM-00001",
                "invoice_type": "Debit Memo",
                "partner_id": 10,
                "purchase_return_id": 5,
                "issue_date": "2026-09-08",
                "due_date": "2026-09-08",
                "total_amount": 350.0,
                "status": "Unpaid",
            }
        ]

        with patch.object(service, "get_debit_memos", return_value=sample_memos) as mock_get, \
             patch.object(service, "count_debit_memos", return_value=1) as mock_count:

            response = client.get("/api/T0090I/debit-memos?purchase_return_id=5&partner_id=10&status=Unpaid")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["invoice_number"] == "DM-00001"
            assert data[0]["purchase_return_id"] == 5
            assert response.headers.get("X-Total-Count") == "1"


            mock_get.assert_called_once_with(
                purchase_return_id=5,
                partner_id=10,
                status="Unpaid",
                limit=50,
                offset=0,
                order_by=None,
            )
            mock_count.assert_called_once_with(
                purchase_return_id=5,
                partner_id=10,
                status="Unpaid",
            )


    def test_get_debit_memo_by_purchase_return_endpoint_success(self, client):
        sample_memo = {
            "id": 20,
            "invoice_number": "DM-00020",
            "invoice_type": "Debit Memo",
            "partner_id": 4,
            "purchase_return_id": 8,
            "issue_date": "2026-09-08",
            "due_date": "2026-09-08",
            "total_amount": 750.0,
            "status": "Unpaid",
        }


        with patch.object(service, "get_debit_memo_by_purchase_return", return_value=sample_memo) as mock_get:
            response = client.get("/api/T0090I/by-purchase-return/8")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == 20
            assert data["purchase_return_id"] == 8
            assert data["total_amount"] == 750.0
            mock_get.assert_called_once_with(8)

    def test_get_debit_memo_by_purchase_return_endpoint_not_found(self, client):
        with patch.object(service, "get_debit_memo_by_purchase_return", return_value=None):
            response = client.get("/api/T0090I/by-purchase-return/999")
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "No debit memo found" in response.json()["detail"]


    def test_get_debit_memo_rma_alias_endpoint(self, client):
        sample_memo = {
            "id": 21,
            "invoice_number": "DM-00021",
            "invoice_type": "Debit Memo",
            "partner_id": 4,
            "purchase_return_id": 9,
            "issue_date": "2026-09-08",
            "due_date": "2026-09-08",
            "total_amount": 420.0,
            "status": "Unpaid",
        }

        with patch.object(service, "get_debit_memo_by_purchase_return", return_value=sample_memo) as mock_get:
            response = client.get("/api/T0090I/rma/9")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == 21
            assert data["purchase_return_id"] == 9
            mock_get.assert_called_once_with(9)
