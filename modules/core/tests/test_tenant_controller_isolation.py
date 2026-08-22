import json
from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from modules.core.controllers.base import create_crud_router, check_record_ownership
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.context import tenant_context, clear_current_tenant
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
