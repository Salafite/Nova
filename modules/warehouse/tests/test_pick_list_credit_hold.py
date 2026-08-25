import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from modules.warehouse.services.pick_list_service import PickListService
from modules.warehouse.controllers import T0101I


class TestPickListCreditHoldProtection:
    def setup_method(self):
        self.pl_repo = MagicMock()
        self.pli_repo = MagicMock()
        self.order_repo = MagicMock()
        self.line_repo = MagicMock()
        self.wh_repo = MagicMock()
        self.product_repo = MagicMock()
        self.uom_repo = MagicMock()
        self.batch_service = MagicMock()

        self.service = PickListService(
            repo=self.pl_repo,
            pl_repo=self.pl_repo,
            pli_repo=self.pli_repo,
            batch_service=self.batch_service,
            order_repo=self.order_repo,
            line_repo=self.line_repo,
            wh_repo=self.wh_repo,
            product_repo=self.product_repo,
            uom_repo=self.uom_repo,
        )

    def test_create_from_order_blocked_when_order_on_credit_hold(self):
        self.order_repo.get.return_value = {
            'id': 101,
            'order_number': 'SO-00101',
            'customer_id': 10,
            'warehouse_id': 1,
            'status': 'Credit Hold',
            'hold_reason': 'Customer credit limit exceeded ($15,000.00 / $10,000.00)',
        }

        with pytest.raises(ValueError, match="Order is on Credit Hold"):
            self.service.create_from_order(sales_order_id=101)

        self.pl_repo.create.assert_not_called()

    def test_create_blocked_when_payload_has_credit_hold_order(self):
        self.order_repo.get.return_value = {
            'id': 102,
            'order_number': 'SO-00102',
            'customer_id': 10,
            'warehouse_id': 1,
            'status': 'Credit Hold',
        }

        with pytest.raises(ValueError, match="Order is on Credit Hold"):
            self.service.create({'sales_order_id': 102, 'warehouse_id': 1, 'status': 'Pending'})

        self.pl_repo.create.assert_not_called()

    def test_create_from_order_succeeds_when_order_confirmed(self):
        self.order_repo.get.return_value = {
            'id': 103,
            'order_number': 'SO-00103',
            'customer_id': 10,
            'warehouse_id': 1,
            'status': 'Confirmed',
        }
        self.line_repo.list.return_value = [
            {'id': 1, 'sales_order_id': 103, 'product_id': 1, 'product_name': 'Widget A', 'qty': 5, 'line_number': 1}
        ]
        self.product_repo.get.return_value = {'id': 1, 'name': 'Widget A', 'is_catch_weight': False}
        self.batch_service.allocate_fefo_lots.return_value = []
        self.pl_repo.create.return_value = {'id': 50, 'pick_list_number': 'PL-00050', 'sales_order_id': 103, 'status': 'Pending'}
        self.pl_repo.get.return_value = {'id': 50, 'pick_list_number': 'PL-00050', 'sales_order_id': 103, 'status': 'Pending'}
        self.pli_repo.list.return_value = []

        result = self.service.create_from_order(sales_order_id=103)
        assert result is not None
        assert self.pl_repo.create.called

    def test_start_picking_blocked_when_sales_order_on_credit_hold(self):
        self.pl_repo.get.return_value = {
            'id': 51,
            'sales_order_id': 104,
            'status': 'Pending',
        }
        self.order_repo.get.return_value = {
            'id': 104,
            'status': 'Credit Hold',
        }

        with pytest.raises(ValueError, match="Sales order 104 is on Credit Hold"):
            self.service.start_picking(pick_list_id=51)

    def test_complete_picking_blocked_when_sales_order_on_credit_hold(self):
        self.pl_repo.get.return_value = {
            'id': 52,
            'sales_order_id': 105,
            'status': 'In Progress',
        }
        self.order_repo.get.return_value = {
            'id': 105,
            'status': 'Credit Hold',
        }

        with pytest.raises(ValueError, match="Sales order 105 is on Credit Hold"):
            self.service.complete_picking(pick_list_id=52)


class TestPickListControllerCreditHold:
    def test_generate_from_order_endpoint_blocked_on_credit_hold(self):
        with patch.object(T0101I, 'pl_service') as mock_service:
            mock_service.create_from_order.side_effect = ValueError(
                "Cannot generate pick list for sales order 101: Order is on Credit Hold"
            )
            with pytest.raises(HTTPException) as exc_info:
                T0101I.generate_pick_list_from_order(order_id=101, body={})
            assert exc_info.value.status_code == 400
            assert "Credit Hold" in exc_info.value.detail

    def test_generate_from_order_endpoint_not_found(self):
        with patch.object(T0101I, 'pl_service') as mock_service:
            mock_service.create_from_order.side_effect = ValueError(
                "Sales order 999 not found"
            )
            with pytest.raises(HTTPException) as exc_info:
                T0101I.generate_pick_list_from_order(order_id=999, body={})
            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail
