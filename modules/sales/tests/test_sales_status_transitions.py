import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from modules.sales.services.sales_service import SalesOrderService, VALID_SALES_STATUS_TRANSITIONS


class TestSalesOrderStatusTransitions:
    @pytest.fixture
    def sales_service_with_mock_repo(self):
        order_repo = MagicMock()
        line_repo = MagicMock()
        orders = {}

        def mock_get(id_val, conn=None):
            return dict(orders[id_val]) if id_val in orders else None

        def mock_update(id_val, payload, conn=None):
            if id_val in orders:
                orders[id_val].update(payload)
                return dict(orders[id_val])
            return None

        order_repo.get.side_effect = mock_get
        order_repo.update.side_effect = mock_update

        svc = SalesOrderService(repo=order_repo, line_repo=line_repo)
        # Mock internal helper methods that require db / inventory
        svc._reserve_order_stock = MagicMock()
        svc._release_order_stock = MagicMock()
        svc._validate_delivery_tolerance_approvals = MagicMock()
        svc._create_invoice_from_order = MagicMock()

        return svc, orders

    def test_valid_sales_status_transitions_definition(self):
        assert 'Credit Hold' in VALID_SALES_STATUS_TRANSITIONS
        assert set(VALID_SALES_STATUS_TRANSITIONS['Credit Hold']) == {'Draft', 'Pending', 'Confirmed', 'Cancelled'}
        assert 'Credit Hold' in VALID_SALES_STATUS_TRANSITIONS['Draft']
        assert 'Credit Hold' in VALID_SALES_STATUS_TRANSITIONS['Pending']

    @pytest.mark.parametrize('target_status', ['Draft', 'Pending', 'Confirmed', 'Cancelled'])
    def test_valid_transitions_from_credit_hold(self, sales_service_with_mock_repo, target_status):
        svc, orders = sales_service_with_mock_repo
        orders[1] = {'id': 1, 'order_number': 'SO-001', 'status': 'Credit Hold'}

        result = svc.update(1, {'status': target_status})
        assert result['status'] == target_status

    @pytest.mark.parametrize('invalid_target', ['Shipped', 'Delivered', 'Invoiced', 'Paid'])
    def test_invalid_transitions_from_credit_hold(self, sales_service_with_mock_repo, invalid_target):
        svc, orders = sales_service_with_mock_repo
        orders[1] = {'id': 1, 'order_number': 'SO-001', 'status': 'Credit Hold'}

        with pytest.raises(HTTPException) as exc_info:
            svc.update(1, {'status': invalid_target})

        assert exc_info.value.status_code == 400
        assert f"Invalid status transition: Credit Hold -> {invalid_target}" in exc_info.value.detail

    @pytest.mark.parametrize('initial_status', ['Draft', 'Pending'])
    def test_valid_transitions_to_credit_hold(self, sales_service_with_mock_repo, initial_status):
        svc, orders = sales_service_with_mock_repo
        orders[2] = {'id': 2, 'order_number': 'SO-002', 'status': initial_status}

        result = svc.update(2, {'status': 'Credit Hold', 'hold_reason': 'Credit limit check failed'})
        assert result['status'] == 'Credit Hold'

    @pytest.mark.parametrize('initial_status', ['Shipped', 'Delivered', 'Invoiced', 'Paid', 'Cancelled'])
    def test_invalid_transitions_to_credit_hold(self, sales_service_with_mock_repo, initial_status):
        svc, orders = sales_service_with_mock_repo
        orders[3] = {'id': 3, 'order_number': 'SO-003', 'status': initial_status}

        with pytest.raises(HTTPException) as exc_info:
            svc.update(3, {'status': 'Credit Hold'})

        assert exc_info.value.status_code == 400
        assert f"Invalid status transition: {initial_status} -> Credit Hold" in exc_info.value.detail
