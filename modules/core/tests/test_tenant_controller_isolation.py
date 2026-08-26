import json
from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from modules.core.controllers.base import create_crud_router, check_record_ownership
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.context import tenant_context, clear_current_tenant, get_current_tenant
from packages.auth.jwt import create_access_token
from apps.api.main import app


class DummyCreate(BaseModel):
    name: str


class DummyUpdate(BaseModel):
    name: str = None


class DummyResponse(BaseModel):
    id: int
    name: str
    business_id: int = None


class TestCheckRecordOwnership:
    def setup_method(self):
        clear_current_tenant()

    def teardown_method(self):
        clear_current_tenant()

    def test_check_record_ownership_raises_403_on_cross_tenant_access(self):
        mock_service = MagicMock(spec=CrudService)
        mock_service.get_unscoped.return_value = {"id": 42, "name": "Secret Data", "business_id": 2}

        with tenant_context(1):
            with patch("modules.core.controllers.base.record_security_event") as mock_audit:
                with pytest.raises(HTTPException) as exc:
                    check_record_ownership(
                        target=mock_service,
                        id_val=42,
                        user={"id": 10, "username": "attacker"},
                        table_name="T0001",
                        method="GET",
                    )
                assert exc.value.status_code == 403
                assert "cross-tenant access forbidden" in exc.value.detail

                mock_audit.assert_called_once()
                call_args, call_kwargs = mock_audit.call_args
                assert call_kwargs["table_name"] == "T0001"
                assert call_kwargs["record_id"] == 42
                assert call_kwargs["action"] == "CROSS_TENANT_ACCESS"
                assert call_kwargs["user_id"] == 10
                assert call_kwargs["business_id"] == 1
                assert call_kwargs["target_tenant_id"] == 2
                assert call_kwargs["details"]["method"] == "GET"

    def test_check_record_ownership_does_not_raise_when_record_not_found(self):
        mock_service = MagicMock(spec=CrudService)
        mock_service.get_unscoped.return_value = None

        with tenant_context(1):
            with patch("modules.core.controllers.base.record_security_event") as mock_audit:
                check_record_ownership(
                    target=mock_service,
                    id_val=999,
                    user={"id": 10},
                    table_name="T0001",
                )
                assert not mock_audit.called

    def test_check_record_ownership_does_not_raise_when_tenant_matches(self):
        mock_service = MagicMock(spec=CrudService)
        mock_service.get_unscoped.return_value = {"id": 1, "business_id": 1}

        with tenant_context(1):
            with patch("modules.core.controllers.base.record_security_event") as mock_audit:
                check_record_ownership(
                    target=mock_service,
                    id_val=1,
                    user={"id": 10},
                    table_name="T0001",
                )
                assert not mock_audit.called

    def test_check_record_ownership_handles_repo_target(self):
        mock_repo = MagicMock(spec=CrudRepository)
        mock_repo.get_unscoped.return_value = {"id": 5, "business_id": 99}
        mock_repo.table = "T0010"

        with tenant_context(1):
            with patch("modules.core.controllers.base.record_security_event") as mock_audit:
                with pytest.raises(HTTPException) as exc:
                    check_record_ownership(
                        target=mock_repo,
                        id_val=5,
                        user={"id": 7},
                        method="DELETE",
                    )
                assert exc.value.status_code == 403
                assert mock_audit.called
                assert mock_audit.call_args[1]["table_name"] == "T0010"
                assert mock_audit.call_args[1]["target_tenant_id"] == 99


class TestControllerCrudTenantScoping:
    """Integration test suite for create_crud_router with tenant isolation and security audits."""

    def setup_method(self):
        clear_current_tenant()

    def teardown_method(self):
        clear_current_tenant()

    def test_get_one_same_tenant_returns_200(self):
        test_client = TestClient(app)
        token = create_access_token(1, business_id=1)
        user = {"id": 1, "username": "admin", "role": "Admin", "permissions": ["*"], "business_id": 1}

        sample_uom = {
            "id": 10,
            "uom_code": "PCS",
            "uom_name": "Pieces",
            "category": "Count",
            "is_base_unit": True,
            "is_active": True,
            "business_id": 1,
        }

        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=sample_uom):

            resp = test_client.get("/api/T0001I/10", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == 10
            assert data["uom_code"] == "PCS"

    def test_get_one_cross_tenant_returns_403_and_audits(self):
        test_client = TestClient(app)
        token = create_access_token(1, business_id=1)
        user = {"id": 1, "username": "admin", "role": "Admin", "permissions": ["*"], "business_id": 1}

        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit_create:
            mock_unscoped.return_value = {
                "id": 20,
                "uom_code": "BOX",
                "uom_name": "Box",
                "category": "Packaging",
                "is_base_unit": False,
                "is_active": True,
                "business_id": 2,
            }
            mock_audit_create.return_value = {"id": 1}

            resp = test_client.get("/api/T0001I/20", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]

            assert mock_audit_create.called
            entry = mock_audit_create.call_args[0][0]
            assert entry["table_name"] == "T0001"
            assert entry["record_id"] == 20
            assert entry["action"] == "CROSS_TENANT_ACCESS"
            assert entry["changed_by"] == 1
            assert entry["business_id"] == 1

            payload = json.loads(entry["changed_data"])
            assert payload["tenant_id"] == 1
            assert payload["target_tenant_id"] == 2
            assert payload["details"]["method"] == "GET"

    def test_get_one_not_found_returns_404(self):
        test_client = TestClient(app)
        token = create_access_token(1, business_id=1)
        user = {"id": 1, "username": "admin", "role": "Admin", "permissions": ["*"], "business_id": 1}

        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped", return_value=None), \
             patch("packages.security.audit._audit_repo.create") as mock_audit_create:

            resp = test_client.get("/api/T0001I/999", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 404
            assert not mock_audit_create.called

    def test_update_one_same_tenant_returns_200(self):
        test_client = TestClient(app)
        token = create_access_token(1, business_id=1)
        user = {"id": 1, "username": "admin", "role": "Admin", "permissions": ["*"], "business_id": 1}

        sample_uom = {
            "id": 10,
            "uom_code": "PCS",
            "uom_name": "Pieces",
            "category": "Count",
            "is_base_unit": True,
            "is_active": True,
            "business_id": 1,
        }
        updated_uom = dict(sample_uom, uom_name="Pieces Updated")

        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=sample_uom), \
             patch("modules.core.repositories.base.CrudRepository.update", return_value=updated_uom), \
             patch("modules.core.repositories.base.CrudRepository.create") as mock_audit:
            mock_audit.return_value = {"id": 1}

            resp = test_client.put(
                "/api/T0001I/10",
                headers={"Authorization": f"Bearer {token}"},
                json={"uom_name": "Pieces Updated"},
            )
            assert resp.status_code == 200
            assert resp.json()["uom_name"] == "Pieces Updated"

    def test_update_one_cross_tenant_returns_403_and_audits(self):
        test_client = TestClient(app)
        token = create_access_token(1, business_id=1)
        user = {"id": 1, "username": "admin", "role": "Admin", "permissions": ["*"], "business_id": 1}

        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit_create:
            mock_unscoped.return_value = {
                "id": 30,
                "uom_code": "BOX30",
                "uom_name": "Tenant 2 Box",
                "category": "Packaging",
                "is_base_unit": False,
                "is_active": True,
                "business_id": 2,
            }
            mock_audit_create.return_value = {"id": 1}

            resp = test_client.put(
                "/api/T0001I/30",
                headers={"Authorization": f"Bearer {token}"},
                json={"uom_name": "Tampered Box"},
            )
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]

            assert mock_audit_create.called
            entry = mock_audit_create.call_args[0][0]
            assert entry["table_name"] == "T0001"
            assert entry["record_id"] == 30
            assert entry["action"] == "CROSS_TENANT_ACCESS"
            assert entry["changed_by"] == 1
            assert entry["business_id"] == 1

            payload = json.loads(entry["changed_data"])
            assert payload["tenant_id"] == 1
            assert payload["target_tenant_id"] == 2
            assert payload["details"]["method"] == "PUT"

    def test_delete_one_same_tenant_returns_204(self):
        test_client = TestClient(app)
        token = create_access_token(1, business_id=1)
        user = {"id": 1, "username": "admin", "role": "Admin", "permissions": ["*"], "business_id": 1}

        sample_uom = {
            "id": 10,
            "uom_code": "PCS",
            "uom_name": "Pieces",
            "category": "Count",
            "is_base_unit": True,
            "is_active": True,
            "business_id": 1,
        }

        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=sample_uom), \
             patch("modules.core.repositories.base.CrudRepository.delete", return_value=True), \
             patch("modules.core.repositories.base.CrudRepository.create") as mock_audit:
            mock_audit.return_value = {"id": 1}

            resp = test_client.delete(
                "/api/T0001I/10",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 204

    def test_delete_one_cross_tenant_returns_403_and_audits(self):
        test_client = TestClient(app)
        token = create_access_token(1, business_id=1)
        user = {"id": 1, "username": "admin", "role": "Admin", "permissions": ["*"], "business_id": 1}

        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit_create:
            mock_unscoped.return_value = {
                "id": 40,
                "uom_code": "BOX40",
                "uom_name": "Tenant 2 Item",
                "category": "Packaging",
                "is_base_unit": False,
                "is_active": True,
                "business_id": 2,
            }
            mock_audit_create.return_value = {"id": 1}

            resp = test_client.delete(
                "/api/T0001I/40",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]

            assert mock_audit_create.called
            entry = mock_audit_create.call_args[0][0]
            assert entry["table_name"] == "T0001"
            assert entry["record_id"] == 40
            assert entry["action"] == "CROSS_TENANT_ACCESS"
            assert entry["changed_by"] == 1
            assert entry["business_id"] == 1

            payload = json.loads(entry["changed_data"])
            assert payload["tenant_id"] == 1
            assert payload["target_tenant_id"] == 2
            assert payload["details"]["method"] == "DELETE"

    def test_custom_controller_update_user_role_cross_tenant_returns_403(self):
        test_client = TestClient(app)
        token = create_access_token(1, business_id=1)
        user = {"id": 1, "username": "admin", "role": "Admin", "permissions": ["*"], "business_id": 1}

        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit_create:
            mock_unscoped.return_value = {"id": 99, "username": "other_user", "business_id": 2}
            mock_audit_create.return_value = {"id": 1}

            resp = test_client.put(
                "/api/T0021I/99/role",
                headers={"Authorization": f"Bearer {token}"},
                json={"role": "Manager", "permissions": ["FINANCE_VIEW"]},
            )
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit_create.called


class TestMultiDomainCrossTenantIntegration:
    """Integration tests verifying cross-tenant 403 Forbidden and T0023 audits across ERP domain controllers."""

    def setup_method(self):
        clear_current_tenant()

    def teardown_method(self):
        clear_current_tenant()

    def test_products_crud_cross_tenant_protection(self):
        test_client = TestClient(app)
        token = create_access_token(5, business_id=10)
        user = {"id": 5, "username": "inv_mgr", "role": "Admin", "permissions": ["*"], "business_id": 10}

        sample_product_tenant20 = {
            "id": 100,
            "sku": "WIDGET-01",
            "name": "Tenant 20 Widget",
            "category_id": 1,
            "uom_id": 1,
            "cost_price": 10.0,
            "selling_price": 20.0,
            "is_active": True,
            "business_id": 20,
        }

        # Cross-tenant GET
        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = sample_product_tenant20
            mock_audit.return_value = {"id": 1}

            resp = test_client.get("/api/T0003I/100", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called
            audit_entry = mock_audit.call_args[0][0]
            assert audit_entry["table_name"] == "T0003"
            assert audit_entry["record_id"] == 100
            assert audit_entry["action"] == "CROSS_TENANT_ACCESS"
            assert audit_entry["changed_by"] == 5
            assert audit_entry["business_id"] == 10

        # Cross-tenant PUT
        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = sample_product_tenant20
            mock_audit.return_value = {"id": 1}

            resp = test_client.put(
                "/api/T0003I/100",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": "Hacked Widget"},
            )
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called
            audit_entry = mock_audit.call_args[0][0]
            assert audit_entry["table_name"] == "T0003"
            assert audit_entry["record_id"] == 100
            payload = json.loads(audit_entry["changed_data"])
            assert payload["details"]["method"] == "PUT"

        # Cross-tenant DELETE
        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = sample_product_tenant20
            mock_audit.return_value = {"id": 1}

            resp = test_client.delete("/api/T0003I/100", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called
            audit_entry = mock_audit.call_args[0][0]
            assert audit_entry["table_name"] == "T0003"
            assert audit_entry["record_id"] == 100
            payload = json.loads(audit_entry["changed_data"])
            assert payload["details"]["method"] == "DELETE"

    def test_customers_crud_and_subroutes_cross_tenant_protection(self):
        test_client = TestClient(app)
        token = create_access_token(8, business_id=15)
        user = {"id": 8, "username": "crm_rep", "role": "Admin", "permissions": ["*"], "business_id": 15}

        # Cross-tenant GET customer
        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = {"id": 250, "name": "Acme Corp", "business_id": 99}
            mock_audit.return_value = {"id": 1}

            resp = test_client.get("/api/T0010I/250", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called
            assert mock_audit.call_args[0][0]["table_name"] == "T0010"
            assert mock_audit.call_args[0][0]["record_id"] == 250

        # Customer Aging subroute: GET /api/T0010I/{id}/aging
        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = {"id": 250, "name": "Acme Corp", "business_id": 99}
            mock_audit.return_value = {"id": 1}

            resp = test_client.get("/api/T0010I/250/aging", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called

        # Customer Payments subroute: GET /api/T0010I/{id}/payments
        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = {"id": 250, "name": "Acme Corp", "business_id": 99}
            mock_audit.return_value = {"id": 1}

            resp = test_client.get("/api/T0010I/250/payments", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called

        # Customer Invoices subroute: GET /api/T0010I/{id}/invoices
        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = {"id": 250, "name": "Acme Corp", "business_id": 99}
            mock_audit.return_value = {"id": 1}

            resp = test_client.get("/api/T0010I/250/invoices", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called

    def test_sales_orders_confirm_and_cancel_cross_tenant_protection(self):
        test_client = TestClient(app)
        token = create_access_token(3, business_id=1)
        user = {"id": 3, "username": "sales_admin", "role": "Admin", "permissions": ["*"], "business_id": 1}

        # POST /api/T0012I/{id}/confirm
        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = {"id": 501, "order_number": "SO-501", "status": "Draft", "business_id": 2}
            mock_audit.return_value = {"id": 1}

            resp = test_client.post("/api/T0012I/501/confirm", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called
            entry = mock_audit.call_args[0][0]
            assert entry["table_name"] == "T0012"
            assert entry["record_id"] == 501
            assert entry["action"] == "CROSS_TENANT_ACCESS"
            assert entry["changed_by"] == 3
            assert entry["business_id"] == 1

        # POST /api/T0012I/{id}/cancel
        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = {"id": 502, "order_number": "SO-502", "status": "Draft", "business_id": 2}
            mock_audit.return_value = {"id": 1}

            resp = test_client.post("/api/T0012I/502/cancel", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called
            entry = mock_audit.call_args[0][0]
            assert entry["table_name"] == "T0012"
            assert entry["record_id"] == 502
            assert entry["action"] == "CROSS_TENANT_ACCESS"

    def test_sales_returns_custom_actions_cross_tenant_protection(self):
        test_client = TestClient(app)
        token = create_access_token(12, business_id=100)
        user = {"id": 12, "username": "returns_rep", "role": "Admin", "permissions": ["*"], "business_id": 100}

        # POST /api/T0079I/{id}/approve
        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = {"id": 701, "status": "Draft", "business_id": 200}
            mock_audit.return_value = {"id": 1}

            resp = test_client.post("/api/T0079I/701/approve", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called
            assert mock_audit.call_args[0][0]["table_name"] == "T0079"
            assert mock_audit.call_args[0][0]["record_id"] == 701

        # POST /api/T0079I/{id}/receive
        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = {"id": 702, "status": "Approved", "business_id": 200}
            mock_audit.return_value = {"id": 1}

            resp = test_client.post("/api/T0079I/702/receive", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called

        # POST /api/T0079I/{id}/cancel
        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = {"id": 703, "status": "Draft", "business_id": 200}
            mock_audit.return_value = {"id": 1}

            resp = test_client.post("/api/T0079I/703/cancel", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called

    def test_invoices_cross_tenant_protection(self):
        test_client = TestClient(app)
        token = create_access_token(6, business_id=4)
        user = {"id": 6, "username": "accountant", "role": "Admin", "permissions": ["*"], "business_id": 4}

        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = {"id": 901, "invoice_number": "INV-901", "total_amount": 5000, "business_id": 5}
            mock_audit.return_value = {"id": 1}

            resp = test_client.get("/api/T0090I/901", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called
            assert mock_audit.call_args[0][0]["table_name"] == "T0090"
            assert mock_audit.call_args[0][0]["record_id"] == 901

    def test_settings_and_modules_cross_tenant_protection(self):
        test_client = TestClient(app)
        token = create_access_token(2, business_id=50)
        user = {"id": 2, "username": "sysadmin", "role": "Admin", "permissions": ["*"], "business_id": 50}

        # T0025 Settings: GET
        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = {"id": 25, "setting_key": "app.logo", "business_id": 60}
            mock_audit.return_value = {"id": 1}

            resp = test_client.get("/api/T0025I/25", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called
            assert mock_audit.call_args[0][0]["table_name"] == "T0025"

        # T0100 Module Registry: PUT toggle
        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_unscoped.return_value = {"id": 101, "module_key": "custom_mfg", "is_active": True, "business_id": 60}
            mock_audit.return_value = {"id": 1}

            resp = test_client.put(
                "/api/T0100I/101/toggle",
                headers={"Authorization": f"Bearer {token}"},
                json={"is_active": False},
            )
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert mock_audit.called
            assert mock_audit.call_args[0][0]["table_name"] == "T0100"


class TestBidirectionalAndMultiTenantIsolation:
    """Integration tests validating bidirectional cross-tenant isolation between tenants."""

    def setup_method(self):
        clear_current_tenant()

    def teardown_method(self):
        clear_current_tenant()

    def test_bidirectional_isolation_tenant_a_and_tenant_b(self):
        test_client = TestClient(app)
        user_a = {"id": 101, "username": "user_a", "role": "Admin", "permissions": ["*"], "business_id": 10}
        user_b = {"id": 202, "username": "user_b", "role": "Admin", "permissions": ["*"], "business_id": 20}
        token_a = create_access_token(101, business_id=10)
        token_b = create_access_token(202, business_id=20)

        record_a = {
            "id": 1,
            "uom_code": "PCS-A",
            "uom_name": "Pieces A",
            "category": "Count",
            "is_base_unit": True,
            "is_active": True,
            "business_id": 10,
        }
        record_b = {
            "id": 2,
            "uom_code": "PCS-B",
            "uom_name": "Pieces B",
            "category": "Count",
            "is_base_unit": True,
            "is_active": True,
            "business_id": 20,
        }

        # Tenant A accessing Tenant B's record -> 403 + logged
        with patch("packages.auth.deps.get_user_by_id", return_value=user_a), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped", return_value=record_b), \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_audit.return_value = {"id": 1}

            resp = test_client.get("/api/T0001I/2", headers={"Authorization": f"Bearer {token_a}"})
            assert resp.status_code == 403
            assert mock_audit.called
            entry = mock_audit.call_args[0][0]
            assert entry["business_id"] == 10
            payload = json.loads(entry["changed_data"])
            assert payload["tenant_id"] == 10
            assert payload["target_tenant_id"] == 20

        # Tenant B accessing Tenant A's record -> 403 + logged
        with patch("packages.auth.deps.get_user_by_id", return_value=user_b), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped", return_value=record_a), \
             patch("packages.security.audit._audit_repo.create") as mock_audit:
            mock_audit.return_value = {"id": 2}

            resp = test_client.get("/api/T0001I/1", headers={"Authorization": f"Bearer {token_b}"})
            assert resp.status_code == 403
            assert mock_audit.called
            entry = mock_audit.call_args[0][0]
            assert entry["business_id"] == 20
            payload = json.loads(entry["changed_data"])
            assert payload["tenant_id"] == 20
            assert payload["target_tenant_id"] == 10

        # Tenant A accessing Tenant A's record -> 200 OK without audit
        with patch("packages.auth.deps.get_user_by_id", return_value=user_a), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=record_a), \
             patch("packages.security.audit._audit_repo.create") as mock_audit:

            resp = test_client.get("/api/T0001I/1", headers={"Authorization": f"Bearer {token_a}"})
            assert resp.status_code == 200
            assert not mock_audit.called

        # Tenant B accessing Tenant B's record -> 200 OK without audit
        with patch("packages.auth.deps.get_user_by_id", return_value=user_b), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=record_b), \
             patch("packages.security.audit._audit_repo.create") as mock_audit:

            resp = test_client.get("/api/T0001I/2", headers={"Authorization": f"Bearer {token_b}"})
            assert resp.status_code == 200
            assert not mock_audit.called


class TestCrossTenantSecurityAuditFailClosed:
    """Tests ensuring that security enforcement fails closed (403 Forbidden preserved even if audit logging encounters an error)."""

    def setup_method(self):
        clear_current_tenant()

    def teardown_method(self):
        clear_current_tenant()

    def test_audit_db_error_still_returns_403(self):
        test_client = TestClient(app)
        token = create_access_token(1, business_id=1)
        user = {"id": 1, "username": "admin", "role": "Admin", "permissions": ["*"], "business_id": 1}

        with patch("packages.auth.deps.get_user_by_id", return_value=user), \
             patch("modules.core.repositories.base.CrudRepository.get", return_value=None), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped") as mock_unscoped, \
             patch("packages.security.audit._audit_repo.create", side_effect=Exception("Database connection lost")):
            mock_unscoped.return_value = {"id": 99, "business_id": 2}

            resp = test_client.get("/api/T0001I/99", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]


class TestEndToEndControllerCrossTenantIntegration:
    """Stateful end-to-end integration test suite simulating real database storage across tenants."""

    def setup_method(self):
        clear_current_tenant()

    def teardown_method(self):
        clear_current_tenant()

    def test_full_cross_tenant_crud_workflow_with_t0023_audit_storage(self):
        # Database store holding records across tenants
        db_store = {
            "T0001": {
                1: {"id": 1, "uom_code": "TEN1-UOM", "uom_name": "Tenant 1 Unit", "category": "Count", "is_base_unit": True, "is_active": True, "business_id": 100},
                2: {"id": 2, "uom_code": "TEN2-UOM", "uom_name": "Tenant 2 Unit", "category": "Count", "is_base_unit": True, "is_active": True, "business_id": 200},
            },
            "T0023": {},
        }
        audit_seq = [0]

        def fake_get(self, id, business_id=None):
            active_tenant = business_id if business_id is not None else get_current_tenant()
            table_dict = db_store.get(self.table, {})
            row = table_dict.get(id)
            if not row:
                return None
            if active_tenant is not None and row.get("business_id") != active_tenant:
                return None
            return dict(row)

        def fake_get_unscoped(self, id):
            table_dict = db_store.get(self.table, {})
            row = table_dict.get(id)
            return dict(row) if row else None

        def fake_update(self, id, data, business_id=None):
            active_tenant = business_id if business_id is not None else get_current_tenant()
            table_dict = db_store.get(self.table, {})
            row = table_dict.get(id)
            if not row or (active_tenant is not None and row.get("business_id") != active_tenant):
                return None
            row.update(data)
            return dict(row)

        def fake_delete(self, id, hard=False, business_id=None):
            active_tenant = business_id if business_id is not None else get_current_tenant()
            table_dict = db_store.get(self.table, {})
            row = table_dict.get(id)
            if not row or (active_tenant is not None and row.get("business_id") != active_tenant):
                return False
            del table_dict[id]
            return True

        def fake_create(self, data, business_id=None):
            active_tenant = business_id if business_id is not None else get_current_tenant()
            audit_seq[0] += 1
            new_id = audit_seq[0]
            entry = dict(data, id=new_id)
            if active_tenant is not None and "business_id" not in entry:
                entry["business_id"] = active_tenant
            db_store.setdefault(self.table, {})[new_id] = entry
            return entry

        test_client = TestClient(app)
        user_tenant100 = {"id": 11, "username": "user100", "role": "Admin", "permissions": ["*"], "business_id": 100}
        user_tenant200 = {"id": 22, "username": "user200", "role": "Admin", "permissions": ["*"], "business_id": 200}
        token_tenant100 = create_access_token(11, business_id=100)
        token_tenant200 = create_access_token(22, business_id=200)

        with patch("packages.auth.deps.get_user_by_id", side_effect=lambda uid: user_tenant100 if uid == 11 else user_tenant200), \
             patch("modules.core.repositories.base.CrudRepository.get", fake_get), \
             patch("modules.core.repositories.base.CrudRepository.get_unscoped", fake_get_unscoped), \
             patch("modules.core.repositories.base.CrudRepository.update", fake_update), \
             patch("modules.core.repositories.base.CrudRepository.delete", fake_delete), \
             patch("modules.core.repositories.base.CrudRepository.create", fake_create):

            # 1. Tenant 100 reads own record (id=1) -> 200 OK
            resp = test_client.get("/api/T0001I/1", headers={"Authorization": f"Bearer {token_tenant100}"})
            assert resp.status_code == 200
            assert resp.json()["uom_code"] == "TEN1-UOM"
            assert len(db_store["T0023"]) == 0

            # 2. Tenant 100 attempts GET on Tenant 200 record (id=2) -> 403 Forbidden & audits in T0023
            resp = test_client.get("/api/T0001I/2", headers={"Authorization": f"Bearer {token_tenant100}"})
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert len(db_store["T0023"]) == 1

            audit_1 = list(db_store["T0023"].values())[0]
            assert audit_1["table_name"] == "T0001"
            assert audit_1["record_id"] == 2
            assert audit_1["action"] == "CROSS_TENANT_ACCESS"
            assert audit_1["changed_by"] == 11
            assert audit_1["business_id"] == 100
            payload_1 = json.loads(audit_1["changed_data"])
            assert payload_1["tenant_id"] == 100
            assert payload_1["target_tenant_id"] == 200
            assert payload_1["details"]["method"] == "GET"

            # 3. Tenant 100 attempts PUT on Tenant 200 record (id=2) -> 403 Forbidden & audits in T0023
            resp = test_client.put(
                "/api/T0001I/2",
                headers={"Authorization": f"Bearer {token_tenant100}"},
                json={"uom_name": "Tampered Unit"},
            )
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert len(db_store["T0023"]) == 2

            # Verify Tenant 200 data in db_store was NOT tampered with
            assert db_store["T0001"][2]["uom_name"] == "Tenant 2 Unit"

            audit_2 = list(db_store["T0023"].values())[1]
            assert audit_2["table_name"] == "T0001"
            assert audit_2["record_id"] == 2
            assert audit_2["action"] == "CROSS_TENANT_ACCESS"
            payload_2 = json.loads(audit_2["changed_data"])
            assert payload_2["details"]["method"] == "PUT"

            # 4. Tenant 100 attempts DELETE on Tenant 200 record (id=2) -> 403 Forbidden & audits in T0023
            resp = test_client.delete(
                "/api/T0001I/2",
                headers={"Authorization": f"Bearer {token_tenant100}"},
            )
            assert resp.status_code == 403
            assert "cross-tenant access forbidden" in resp.json()["detail"]
            assert len(db_store["T0023"]) == 3
            # Verify Tenant 200 record still exists
            assert 2 in db_store["T0001"]

            audit_3 = list(db_store["T0023"].values())[2]
            payload_3 = json.loads(audit_3["changed_data"])
            assert payload_3["details"]["method"] == "DELETE"

            # 5. Tenant 100 queries a non-existent record (id=999) -> 404 Not Found (no new T0023 entry)
            resp = test_client.get("/api/T0001I/999", headers={"Authorization": f"Bearer {token_tenant100}"})
            assert resp.status_code == 404
            assert len(db_store["T0023"]) == 3

            # 6. Tenant 200 accesses its own record (id=2) -> 200 OK
            resp = test_client.get("/api/T0001I/2", headers={"Authorization": f"Bearer {token_tenant200}"})
            assert resp.status_code == 200
            assert resp.json()["uom_name"] == "Tenant 2 Unit"
            assert len(db_store["T0023"]) == 3

    def test_full_cross_tenant_pagination_isolation_and_query_capping(self):
        """Verify that list pagination, total counts, and link headers are strictly isolated across tenants with zero cross-tenant leakage."""
        db_store = {
            "T0001": {
                # 80 items for Tenant 100
                **{
                    i: {
                        "id": i,
                        "uom_code": f"T100-UOM-{i:03d}",
                        "uom_name": f"Tenant 100 Unit {i}",
                        "category": "Count",
                        "is_base_unit": True,
                        "is_active": True,
                        "business_id": 100,
                    }
                    for i in range(1, 81)
                },
                # 25 items for Tenant 200
                **{
                    i + 500: {
                        "id": i + 500,
                        "uom_code": f"T200-UOM-{i:03d}",
                        "uom_name": f"Tenant 200 Unit {i}",
                        "category": "Count",
                        "is_base_unit": True,
                        "is_active": True,
                        "business_id": 200,
                    }
                    for i in range(1, 26)
                },
            }
        }

        def fake_list(self, filters=None, order_by=None, limit=None, offset=None, conn=None, business_id=None):
            active_tenant = business_id if business_id is not None else get_current_tenant()
            table_dict = db_store.get(self.table, {})
            rows = [dict(v) for v in table_dict.values()]
            if active_tenant is not None and self._has_business_id():
                rows = [r for r in rows if r.get("business_id") == active_tenant]
            if order_by and order_by.startswith("-"):
                col = order_by.lstrip("-")
                rows = sorted(rows, key=lambda x: x.get(col, 0), reverse=True)
            elif order_by:
                rows = sorted(rows, key=lambda x: x.get(order_by, 0))
            else:
                rows = sorted(rows, key=lambda x: x.get("id", 0))

            off = offset or 0
            lim = limit if limit is not None else 50
            return rows[off:off + lim]

        def fake_count(self, filters=None, conn=None, business_id=None):
            active_tenant = business_id if business_id is not None else get_current_tenant()
            table_dict = db_store.get(self.table, {})
            rows = list(table_dict.values())
            if active_tenant is not None and self._has_business_id():
                rows = [r for r in rows if r.get("business_id") == active_tenant]
            return len(rows)

        test_client = TestClient(app)
        user_tenant100 = {"id": 11, "username": "user100", "role": "Admin", "permissions": ["*"], "business_id": 100}
        user_tenant200 = {"id": 22, "username": "user200", "role": "Admin", "permissions": ["*"], "business_id": 200}
        token_tenant100 = create_access_token(11, business_id=100)
        token_tenant200 = create_access_token(22, business_id=200)

        with patch("packages.auth.deps.get_user_by_id", side_effect=lambda uid: user_tenant100 if uid == 11 else user_tenant200), \
             patch("modules.core.repositories.base.CrudRepository.list", fake_list), \
             patch("modules.core.repositories.base.CrudRepository.count", fake_count):

            # --- Tenant 100: Page 1 (limit 50, offset 0) ---
            resp1 = test_client.get("/api/T0001I/?limit=50&offset=0", headers={"Authorization": f"Bearer {token_tenant100}"})
            assert resp1.status_code == 200
            data1 = resp1.json()
            assert len(data1) == 50
            assert all(item["business_id"] == 100 for item in data1)
            assert data1[0]["uom_code"] == "T100-UOM-001"
            assert data1[-1]["uom_code"] == "T100-UOM-050"
            assert resp1.headers.get("X-Total-Count") == "80"
            assert resp1.headers.get("X-Page-Limit") == "50"
            assert resp1.headers.get("X-Page-Offset") == "0"
            assert 'rel="first"' in resp1.headers.get("Link", "")
            assert 'rel="next"' in resp1.headers.get("Link", "")
            assert 'rel="last"' in resp1.headers.get("Link", "")
            assert 'rel="prev"' not in resp1.headers.get("Link", "")

            # --- Tenant 100: Page 2 (limit 50, offset 50) ---
            resp2 = test_client.get("/api/T0001I/?limit=50&offset=50", headers={"Authorization": f"Bearer {token_tenant100}"})
            assert resp2.status_code == 200
            data2 = resp2.json()
            assert len(data2) == 30
            assert all(item["business_id"] == 100 for item in data2)
            assert data2[0]["uom_code"] == "T100-UOM-051"
            assert data2[-1]["uom_code"] == "T100-UOM-080"
            assert resp2.headers.get("X-Total-Count") == "80"
            assert 'rel="prev"' in resp2.headers.get("Link", "")
            assert 'rel="next"' not in resp2.headers.get("Link", "")

            # --- Tenant 100: Page 3 (offset 100 > total 80) -> Empty, Zero leakage of Tenant 200's items ---
            resp3 = test_client.get("/api/T0001I/?limit=50&offset=100", headers={"Authorization": f"Bearer {token_tenant100}"})
            assert resp3.status_code == 200
            data3 = resp3.json()
            assert len(data3) == 0
            assert resp3.headers.get("X-Total-Count") == "80"

            # --- Tenant 200: Page 1 (limit 50, offset 0) -> Exactly 25 items, zero leak from Tenant 100 ---
            resp4 = test_client.get("/api/T0001I/?limit=50&offset=0", headers={"Authorization": f"Bearer {token_tenant200}"})
            assert resp4.status_code == 200
            data4 = resp4.json()
            assert len(data4) == 25
            assert all(item["business_id"] == 200 for item in data4)
            assert data4[0]["uom_code"] == "T200-UOM-001"
            assert data4[-1]["uom_code"] == "T200-UOM-025"
            assert resp4.headers.get("X-Total-Count") == "25"
            assert 'rel="next"' not in resp4.headers.get("Link", "")

            # --- Query capping: limit=500 returns all 80 items for Tenant 100 ---
            resp5 = test_client.get("/api/T0001I/?limit=500&offset=0", headers={"Authorization": f"Bearer {token_tenant100}"})
            assert resp5.status_code == 200
            data5 = resp5.json()
            assert len(data5) == 80

            # --- Query validation: limit=600 is rejected with 422 ---
            resp6 = test_client.get("/api/T0001I/?limit=600&offset=0", headers={"Authorization": f"Bearer {token_tenant100}"})
            assert resp6.status_code == 422



