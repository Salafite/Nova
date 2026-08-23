import pytest
from unittest.mock import MagicMock, patch
from modules.warehouse.services.pick_list_service import PickListService
from modules.warehouse.controllers import T0101I



class TestWeightVarianceCalculation:
    def setup_method(self):
        self.service = PickListService(MagicMock())

    def test_positive_variance(self):
        # Nominal 40kg, actual 42kg => +5.0%
        var = self.service.calculate_weight_variance(nominal_weight=40.0, actual_weight=42.0)
        assert var == 5.0

    def test_negative_variance(self):
        # Nominal 80kg, actual 78.4kg => -2.0%
        var = self.service.calculate_weight_variance(nominal_weight=80.0, actual_weight=78.4)
        assert var == -2.0

    def test_zero_variance(self):
        var = self.service.calculate_weight_variance(nominal_weight=50.0, actual_weight=50.0)
        assert var == 0.0

    def test_rounding_to_two_decimals(self):
        # Nominal 38kg, actual 41.2kg => 8.42105... -> 8.42%
        var = self.service.calculate_weight_variance(nominal_weight=38.0, actual_weight=41.2)
        assert var == 8.42

    def test_actual_weight_none_returns_none(self):
        var = self.service.calculate_weight_variance(nominal_weight=50.0, actual_weight=None)
        assert var is None

    def test_nominal_weight_none_or_zero_returns_none(self):
        assert self.service.calculate_weight_variance(nominal_weight=None, actual_weight=50.0) is None
        assert self.service.calculate_weight_variance(nominal_weight=0, actual_weight=50.0) is None
        assert self.service.calculate_weight_variance(nominal_weight=-10.0, actual_weight=50.0) is None


class TestToleranceEvaluation:
    def setup_method(self):
        self.service = PickListService(MagicMock())

    def test_within_tolerance(self):
        var, status = self.service.evaluate_tolerance(
            nominal_weight=80.0,
            actual_weight=78.4,
            tolerance_pct=5.0
        )
        assert var == -2.0
        assert status == "Within Tolerance"

    def test_exact_tolerance_boundary(self):
        # +5.0% boundary
        var, status = self.service.evaluate_tolerance(
            nominal_weight=100.0,
            actual_weight=105.0,
            tolerance_pct=5.0
        )
        assert var == 5.0
        assert status == "Within Tolerance"

        # -5.0% boundary
        var, status = self.service.evaluate_tolerance(
            nominal_weight=100.0,
            actual_weight=95.0,
            tolerance_pct=5.0
        )
        assert var == -5.0
        assert status == "Within Tolerance"

    def test_out_of_tolerance_overweight(self):
        var, status = self.service.evaluate_tolerance(
            nominal_weight=38.0,
            actual_weight=41.2,
            tolerance_pct=5.0,
            supervisor_approved=False
        )
        assert var == 8.42
        assert status == "Out of Tolerance"

    def test_out_of_tolerance_underweight(self):
        var, status = self.service.evaluate_tolerance(
            nominal_weight=50.0,
            actual_weight=44.0,
            tolerance_pct=5.0,
            supervisor_approved=False
        )
        assert var == -12.0
        assert status == "Out of Tolerance"

    def test_out_of_tolerance_approved_by_supervisor(self):
        var, status = self.service.evaluate_tolerance(
            nominal_weight=38.0,
            actual_weight=41.2,
            tolerance_pct=5.0,
            supervisor_approved=True
        )
        assert var == 8.42
        assert status == "Approved"

    def test_none_actual_weight(self):
        var, status = self.service.evaluate_tolerance(
            nominal_weight=50.0,
            actual_weight=None,
            tolerance_pct=5.0
        )
        assert var is None
        assert status == "Not Applicable"

    def test_none_nominal_weight(self):
        var, status = self.service.evaluate_tolerance(
            nominal_weight=None,
            actual_weight=50.0,
            tolerance_pct=5.0
        )
        assert var is None
        assert status == "Within Tolerance"


class TestPickListCatchWeightPicking:
    def setup_method(self):
        self.mock_pl_repo = MagicMock()
        self.mock_pli_repo = MagicMock()
        self.mock_batch_service = MagicMock()
        self.mock_product_repo = MagicMock()
        self.mock_uom_repo = MagicMock()

        self.service = PickListService(
            repo=self.mock_pl_repo,
            pli_repo=self.mock_pli_repo,
            batch_service=self.mock_batch_service,
            product_repo=self.mock_product_repo,
            uom_repo=self.mock_uom_repo,
        )

    def test_pick_item_with_scale_weight_within_tolerance(self):
        self.mock_pli_repo.get.side_effect = [
            {
                'id': 10,
                'pick_list_id': 1,
                'product_id': 20,
                'qty_ordered': 2.0,
                'nominal_weight': 80.0,
                'tolerance_pct': 5.0,
                'catch_weight_uom': 'kg',
                'supervisor_approved': False,
            },
            {
                'id': 10,
                'pick_list_id': 1,
                'product_id': 20,
                'qty_ordered': 2.0,
                'qty_picked': 2.0,
                'nominal_weight': 80.0,
                'catch_weight_actual': 78.4,
                'catch_weight_uom': 'kg',
                'tolerance_pct': 5.0,
                'tolerance_variance_pct': -2.0,
                'tolerance_status': 'Within Tolerance',
                'supervisor_approved': False,
            }
        ]

        result = self.service.pick_item(
            item_id=10,
            qty_picked=2.0,
            catch_weight_actual=78.4,
            catch_weight_uom='kg'
        )

        self.mock_pli_repo.update.assert_called_once_with(10, {
            'qty_picked': 2.0,
            'catch_weight_actual': 78.4,
            'catch_weight_uom': 'kg',
            'tolerance_variance_pct': -2.0,
            'tolerance_status': 'Within Tolerance',
        })
        assert result['tolerance_status'] == 'Within Tolerance'
        assert result['tolerance_variance_pct'] == -2.0

    def test_pick_item_with_scale_weight_out_of_tolerance(self):
        self.mock_pli_repo.get.side_effect = [
            {
                'id': 11,
                'pick_list_id': 1,
                'product_id': 25,
                'qty_ordered': 1.0,
                'nominal_weight': 38.0,
                'tolerance_pct': 5.0,
                'supervisor_approved': False,
            },
            {
                'id': 11,
                'qty_picked': 1.0,
                'catch_weight_actual': 41.2,
                'tolerance_variance_pct': 8.42,
                'tolerance_status': 'Out of Tolerance',
            }
        ]

        result = self.service.pick_item(
            item_id=11,
            qty_picked=1.0,
            catch_weight_actual=41.2,
            catch_weight_uom='kg'
        )

        self.mock_pli_repo.update.assert_called_once_with(11, {
            'qty_picked': 1.0,
            'catch_weight_actual': 41.2,
            'catch_weight_uom': 'kg',
            'tolerance_variance_pct': 8.42,
            'tolerance_status': 'Out of Tolerance',
        })
        assert result['tolerance_status'] == 'Out of Tolerance'

    def test_pick_item_with_supervisor_approved_status_retained(self):
        self.mock_pli_repo.get.side_effect = [
            {
                'id': 12,
                'pick_list_id': 1,
                'product_id': 25,
                'qty_ordered': 1.0,
                'nominal_weight': 38.0,
                'tolerance_pct': 5.0,
                'catch_weight_uom': 'kg',
                'supervisor_approved': True,
            },
            {
                'id': 12,
                'qty_picked': 1.0,
                'catch_weight_actual': 41.2,
                'catch_weight_uom': 'kg',
                'tolerance_variance_pct': 8.42,
                'tolerance_status': 'Approved',
                'supervisor_approved': True,
            }
        ]

        result = self.service.pick_item(
            item_id=12,
            qty_picked=1.0,
            catch_weight_actual=41.2
        )

        self.mock_pli_repo.update.assert_called_once_with(12, {
            'qty_picked': 1.0,
            'catch_weight_actual': 41.2,
            'tolerance_variance_pct': 8.42,
            'tolerance_status': 'Approved',
        })
        assert result['tolerance_status'] == 'Approved'

    def test_pick_item_negative_catch_weight_raises(self):
        self.mock_pli_repo.get.return_value = {
            'id': 10, 'qty_ordered': 5.0
        }
        with pytest.raises(ValueError, match="Catch weight cannot be negative"):
            self.service.pick_item(item_id=10, qty_picked=2.0, catch_weight_actual=-1.5)

    def test_pick_item_negative_nominal_weight_raises(self):
        self.mock_pli_repo.get.return_value = {
            'id': 10, 'qty_ordered': 5.0
        }
        with pytest.raises(ValueError, match="Nominal weight cannot be negative"):
            self.service.pick_item(item_id=10, qty_picked=2.0, catch_weight_actual=10.0, nominal_weight=-5.0)

    def test_pick_item_invalid_tolerance_pct_raises(self):
        self.mock_pli_repo.get.return_value = {
            'id': 10, 'qty_ordered': 5.0
        }
        with pytest.raises(ValueError, match="Tolerance percentage must be between 0 and 100"):
            self.service.pick_item(item_id=10, qty_picked=2.0, catch_weight_actual=10.0, tolerance_pct=150.0)

    def test_pick_item_falls_back_to_product_parameters(self):
        self.mock_pli_repo.get.side_effect = [
            {
                'id': 15,
                'pick_list_id': 1,
                'product_id': 30,
                'qty_ordered': 3.0,
                'nominal_weight': None,
                'tolerance_pct': None,
                'catch_weight_uom': None,
                'supervisor_approved': False,
            },
            {
                'id': 15,
                'nominal_weight': 60.0,
                'tolerance_pct': 5.0,
                'tolerance_status': 'Within Tolerance'
            }
        ]
        self.mock_product_repo.get.return_value = {
            'id': 30,
            'is_catch_weight': True,
            'nominal_weight': 20.0,  # 20kg per unit
            'tolerance_pct': 5.0,
            'pricing_uom_id': 2
        }
        self.mock_uom_repo.get.return_value = {'id': 2, 'uom_code': 'kg'}

        self.service.pick_item(
            item_id=15,
            qty_picked=3.0,
            catch_weight_actual=61.5
        )

        self.mock_pli_repo.update.assert_called_once_with(15, {
            'qty_picked': 3.0,
            'catch_weight_actual': 61.5,
            'catch_weight_uom': 'kg',
            'nominal_weight': 60.0,
            'tolerance_pct': 5.0,
            'tolerance_variance_pct': 2.5,
            'tolerance_status': 'Within Tolerance',
        })


class TestPickListDiscrepancies:
    def setup_method(self):
        self.mock_pli_repo = MagicMock()
        self.service = PickListService(MagicMock(), pli_repo=self.mock_pli_repo)

    def test_check_discrepancies_identifies_unapproved_out_of_tolerance(self):
        self.mock_pli_repo.list.return_value = [
            {'id': 1, 'product_name': 'Item A', 'tolerance_status': 'Within Tolerance', 'supervisor_approved': False},
            {'id': 2, 'product_name': 'Item B', 'tolerance_status': 'Out of Tolerance', 'supervisor_approved': False},
            {'id': 3, 'product_name': 'Item C', 'tolerance_status': 'Approved', 'supervisor_approved': True},
            {'id': 4, 'product_name': 'Item D', 'tolerance_status': 'Not Applicable', 'supervisor_approved': False},
        ]

        discrepancies = self.service.check_pick_list_discrepancies(pick_list_id=10)
        assert len(discrepancies) == 1
        assert discrepancies[0]['id'] == 2
        assert discrepancies[0]['product_name'] == 'Item B'


class TestPickListDualUOMOrderGeneration:
    def setup_method(self):
        self.mock_pl_repo = MagicMock()
        self.mock_pli_repo = MagicMock()
        self.mock_order_repo = MagicMock()
        self.mock_line_repo = MagicMock()
        self.mock_product_repo = MagicMock()
        self.mock_uom_repo = MagicMock()
        self.mock_batch_service = MagicMock()

        self.service = PickListService(
            repo=self.mock_pl_repo,
            pli_repo=self.mock_pli_repo,
            batch_service=self.mock_batch_service,
            order_repo=self.mock_order_repo,
            line_repo=self.mock_line_repo,
            product_repo=self.mock_product_repo,
            uom_repo=self.mock_uom_repo,
        )

    def test_create_from_order_sets_dual_uom_columns(self):
        self.mock_order_repo.get.return_value = {
            'id': 100, 'warehouse_id': 1, 'status': 'Pending'
        }
        self.mock_line_repo.list.return_value = [
            {
                'id': 501, 'sales_order_id': 100, 'product_id': 20,
                'product_name': 'Parmigiano Wheel 40kg', 'qty': 2.0,
                'line_number': 1, 'is_catch_weight': True
            }
        ]
        self.mock_product_repo.get.return_value = {
            'id': 20, 'is_catch_weight': True, 'nominal_weight': 40.0,
            'tolerance_pct': 5.0, 'pricing_uom_id': 1
        }
        self.mock_uom_repo.get.return_value = {'id': 1, 'uom_code': 'kg'}
        self.mock_batch_service.allocate_fefo_lots.return_value = []

        created_items = []
        def mock_create_item(payload):
            created_items.append(payload)
            return dict(payload, id=len(created_items))
        self.mock_pli_repo.create.side_effect = mock_create_item
        self.mock_pli_repo.list.return_value = created_items

        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-00100'):
            self.service.create_from_order(sales_order_id=100, warehouse_id=1)

        assert len(created_items) == 1
        item = created_items[0]
        assert item['product_id'] == 20
        assert item['qty_ordered'] == 2.0
        assert item['catch_weight_uom'] == 'kg'
        assert item['nominal_weight'] == 80.0  # 40kg * 2 units
        assert item['tolerance_pct'] == 5.0
        assert item['tolerance_status'] == 'Not Applicable'
        assert item['supervisor_approved'] is False


class TestPickListControllerEndpointCatchWeight:
    def test_pick_item_controller_passes_catch_weight_params(self, monkeypatch):
        from modules.warehouse.controllers import T0101I

        mock_svc = MagicMock()
        mock_svc.pick_item.return_value = {
            'id': 5,
            'qty_picked': 2.0,
            'catch_weight_actual': 78.4,
            'catch_weight_uom': 'kg',
            'tolerance_variance_pct': -2.0,
            'tolerance_status': 'Within Tolerance'
        }
        monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

        result = T0101I.pick_item(id=100, item_id=5, body={
            'qty_picked': 2.0,
            'catch_weight_actual': 78.4,
            'catch_weight_uom': 'kg',
            'nominal_weight': 80.0,
            'tolerance_pct': 5.0
        })

        assert result['catch_weight_actual'] == 78.4
        assert result['tolerance_status'] == 'Within Tolerance'
        mock_svc.pick_item.assert_called_once_with(
            item_id=5,
            qty_picked=2.0,
            pick_list_id=100,
            picked_batch_id=None,
            picked_batch_number=None,
            catch_weight_actual=78.4,
            catch_weight_uom='kg',
            nominal_weight=80.0,
            tolerance_pct=5.0
        )


class TestPickListToleranceApproval:
    def setup_method(self):
        self.mock_pl_repo = MagicMock()
        self.mock_pli_repo = MagicMock()
        self.service = PickListService(
            repo=self.mock_pl_repo,
            pli_repo=self.mock_pli_repo,
        )

    def test_approve_tolerance_single_item(self):
        self.mock_pl_repo.get.return_value = {'id': 1, 'pick_list_number': 'PKL-001'}
        self.mock_pli_repo.get.return_value = {
            'id': 10,
            'pick_list_id': 1,
            'product_id': 50,
            'nominal_weight': 40.0,
            'catch_weight_actual': 45.0,
            'tolerance_pct': 5.0,
            'tolerance_variance_pct': 12.5,
            'tolerance_status': 'Out of Tolerance',
            'supervisor_approved': False,
        }
        self.mock_pli_repo.list.return_value = []

        self.service.approve_tolerance(
            pick_list_id=1,
            item_id=10,
            supervisor_id=7,
            supervisor_notes='Overweight approved by QA supervisor',
        )

        self.mock_pli_repo.update.assert_called_once()
        args, kwargs = self.mock_pli_repo.update.call_args
        assert args[0] == 10
        update_data = args[1]
        assert update_data['supervisor_approved'] is True
        assert update_data['supervisor_approved_by'] == 7
        assert update_data['supervisor_notes'] == 'Overweight approved by QA supervisor'
        assert update_data['tolerance_status'] == 'Approved'
        assert update_data['tolerance_variance_pct'] == 12.5
        assert update_data['supervisor_approved_at'] is not None

    def test_approve_tolerance_bulk_item_ids(self):
        self.mock_pl_repo.get.return_value = {'id': 1, 'pick_list_number': 'PKL-001'}
        self.mock_pli_repo.get.side_effect = lambda iid: {
            'id': iid,
            'pick_list_id': 1,
            'nominal_weight': 20.0,
            'catch_weight_actual': 23.0,
            'tolerance_pct': 5.0,
            'tolerance_status': 'Out of Tolerance',
            'supervisor_approved': False,
        }
        self.mock_pli_repo.list.return_value = []

        self.service.approve_tolerance(
            pick_list_id=1,
            item_ids=[10, 11],
            supervisor_id=8,
            notes='Bulk approved',
        )

        assert self.mock_pli_repo.update.call_count == 2
        calls = self.mock_pli_repo.update.call_args_list
        assert calls[0][0][0] == 10
        assert calls[0][0][1]['supervisor_approved'] is True
        assert calls[0][0][1]['supervisor_approved_by'] == 8
        assert calls[0][0][1]['supervisor_notes'] == 'Bulk approved'
        assert calls[0][0][1]['tolerance_status'] == 'Approved'

        assert calls[1][0][0] == 11
        assert calls[1][0][1]['supervisor_approved'] is True
        assert calls[1][0][1]['supervisor_approved_by'] == 8
        assert calls[1][0][1]['supervisor_notes'] == 'Bulk approved'

    def test_approve_tolerance_all_out_of_tolerance_items(self):
        self.mock_pl_repo.get.return_value = {'id': 1, 'pick_list_number': 'PKL-001'}
        self.mock_pli_repo.list.return_value = [
            {'id': 10, 'pick_list_id': 1, 'nominal_weight': 40.0, 'catch_weight_actual': 44.0, 'tolerance_pct': 5.0, 'tolerance_status': 'Out of Tolerance', 'supervisor_approved': False},
            {'id': 11, 'pick_list_id': 1, 'nominal_weight': 40.0, 'catch_weight_actual': 40.2, 'tolerance_pct': 5.0, 'tolerance_status': 'Within Tolerance', 'supervisor_approved': False},
            {'id': 12, 'pick_list_id': 1, 'nominal_weight': 50.0, 'catch_weight_actual': 56.0, 'tolerance_pct': 5.0, 'tolerance_status': 'Out of Tolerance', 'supervisor_approved': False},
        ]

        self.service.approve_tolerance(
            pick_list_id=1,
            supervisor_id=9,
            supervisor_notes='Approve all discrepancies',
        )

        assert self.mock_pli_repo.update.call_count == 2
        updated_ids = [call[0][0] for call in self.mock_pli_repo.update.call_args_list]
        assert updated_ids == [10, 12]

    def test_approve_tolerance_pick_list_not_found_raises(self):
        self.mock_pl_repo.get.return_value = None
        with pytest.raises(ValueError, match="Pick list 999 not found"):
            self.service.approve_tolerance(pick_list_id=999)

    def test_approve_tolerance_item_not_found_raises(self):
        self.mock_pl_repo.get.return_value = {'id': 1}
        self.mock_pli_repo.get.return_value = None
        with pytest.raises(ValueError, match="Pick list item 888 not found"):
            self.service.approve_tolerance(pick_list_id=1, item_id=888)

    def test_approve_tolerance_item_wrong_pick_list_raises(self):
        self.mock_pl_repo.get.return_value = {'id': 1}
        self.mock_pli_repo.get.return_value = {'id': 10, 'pick_list_id': 2}
        with pytest.raises(ValueError, match="does not belong to pick list 1"):
            self.service.approve_tolerance(pick_list_id=1, item_id=10)

    def test_approve_item_tolerance_helper(self):
        self.mock_pl_repo.get.return_value = {'id': 1}
        self.mock_pli_repo.get.return_value = {
            'id': 10,
            'pick_list_id': 1,
            'nominal_weight': 10.0,
            'catch_weight_actual': 12.0,
            'tolerance_pct': 5.0,
            'tolerance_status': 'Out of Tolerance',
            'supervisor_approved': False,
        }
        self.mock_pli_repo.list.return_value = []

        self.service.approve_item_tolerance(
            pick_list_id=1,
            item_id=10,
            supervisor_id=3,
            notes='Helper approval',
        )

        self.mock_pli_repo.update.assert_called_once()
        args, _ = self.mock_pli_repo.update.call_args
        assert args[0] == 10
        assert args[1]['supervisor_approved'] is True
        assert args[1]['supervisor_approved_by'] == 3
        assert args[1]['supervisor_notes'] == 'Helper approval'


class TestPickListCompletePickingCatchWeightGating:
    def setup_method(self):
        self.mock_pl_repo = MagicMock()
        self.mock_pli_repo = MagicMock()
        self.mock_order_repo = MagicMock()
        self.mock_batch_service = MagicMock()

        self.service = PickListService(
            repo=self.mock_pl_repo,
            pli_repo=self.mock_pli_repo,
            order_repo=self.mock_order_repo,
            batch_service=self.mock_batch_service,
        )

    def test_complete_picking_blocked_by_unapproved_out_of_tolerance_item(self):
        self.mock_pl_repo.get.return_value = {'id': 1, 'sales_order_id': 100}
        self.mock_pli_repo.list.return_value = [
            {
                'id': 10,
                'product_name': 'Cheddar Block 20kg',
                'qty_ordered': 2.0,
                'qty_picked': 2.0,
                'tolerance_status': 'Out of Tolerance',
                'supervisor_approved': False,
            }
        ]

        with pytest.raises(ValueError, match="Unapproved catch-weight tolerance discrepancies exist"):
            self.service.complete_picking(pick_list_id=1)

        self.mock_pl_repo.update.assert_not_called()
        self.mock_order_repo.update.assert_not_called()

    def test_complete_picking_succeeds_after_supervisor_approval(self):
        self.mock_pl_repo.get.return_value = {'id': 1, 'sales_order_id': 100}
        self.mock_pli_repo.list.return_value = [
            {
                'id': 10,
                'product_name': 'Cheddar Block 20kg',
                'qty_ordered': 2.0,
                'qty_picked': 2.0,
                'tolerance_status': 'Approved',
                'supervisor_approved': True,
                'batch_id': None,
                'picked_batch_id': None,
                'batch_number': None,
                'picked_batch_number': None,
            }
        ]

        result = self.service.complete_picking(pick_list_id=1)

        self.mock_pl_repo.update.assert_called_once_with(1, {'status': 'Completed'})
        self.mock_order_repo.update.assert_called_once_with(100, {'status': 'Shipped'})
        assert result['has_discrepancies'] is False
        assert result['discrepancy_count'] == 0

    def test_get_with_items_includes_discrepancy_flags(self):
        self.mock_pl_repo.get.return_value = {'id': 1, 'pick_list_number': 'PKL-001'}
        self.mock_pli_repo.list.return_value = [
            {'id': 1, 'qty_ordered': 1, 'qty_picked': 1, 'tolerance_status': 'Out of Tolerance', 'supervisor_approved': False},
            {'id': 2, 'qty_ordered': 1, 'qty_picked': 1, 'tolerance_status': 'Within Tolerance', 'supervisor_approved': False},
        ]

        detail = self.service.get_with_items(1)
        assert detail['has_discrepancies'] is True
        assert detail['discrepancy_count'] == 1


class TestPickListApprovalControllerEndpoints:
    def test_approve_tolerance_controller_endpoint_all_items(self, monkeypatch):
        from modules.warehouse.controllers import T0101I
        from fastapi import HTTPException

        mock_svc = MagicMock()
        mock_svc.approve_tolerance.return_value = {
            'id': 100,
            'status': 'In Progress',
            'has_discrepancies': False,
            'discrepancy_count': 0,
        }
        monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

        result = T0101I.approve_tolerance(
            id=100,
            body={
                'supervisor_id': 5,
                'supervisor_notes': 'All items approved'
            }
        )

        assert result['has_discrepancies'] is False
        mock_svc.approve_tolerance.assert_called_once_with(
            pick_list_id=100,
            item_id=None,
            item_ids=None,
            supervisor_id=5,
            supervisor_notes='All items approved',
        )

    def test_approve_tolerance_controller_endpoint_single_item(self, monkeypatch):
        from modules.warehouse.controllers import T0101I

        mock_svc = MagicMock()
        mock_svc.approve_tolerance.return_value = {
            'id': 100,
            'has_discrepancies': False,
        }
        monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

        result = T0101I.approve_tolerance(
            id=100,
            body={
                'item_id': 15,
                'approved_by': 2,
                'notes': 'Item approved'
            }
        )

        mock_svc.approve_tolerance.assert_called_once_with(
            pick_list_id=100,
            item_id=15,
            item_ids=None,
            supervisor_id=2,
            supervisor_notes='Item approved',
        )

    def test_approve_item_tolerance_controller_endpoint(self, monkeypatch):
        from modules.warehouse.controllers import T0101I

        mock_svc = MagicMock()
        mock_svc.approve_item_tolerance.return_value = {
            'id': 100,
            'has_discrepancies': False,
        }
        monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

        result = T0101I.approve_item_tolerance(
            id=100,
            item_id=15,
            body={
                'supervisor_id': 4,
                'supervisor_notes': 'Approved item 15'
            }
        )

        mock_svc.approve_item_tolerance.assert_called_once_with(
            pick_list_id=100,
            item_id=15,
            supervisor_id=4,
            supervisor_notes='Approved item 15',
        )

    def test_get_pick_list_discrepancies_controller_endpoint(self, monkeypatch):
        from modules.warehouse.controllers import T0101I

        mock_svc = MagicMock()
        mock_svc.check_pick_list_discrepancies.return_value = [
            {'id': 15, 'product_name': 'Cheese', 'tolerance_status': 'Out of Tolerance'}
        ]
        monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

        result = T0101I.get_pick_list_discrepancies(id=100)
        assert len(result) == 1
        assert result[0]['id'] == 15
        mock_svc.check_pick_list_discrepancies.assert_called_once_with(100)

    def test_approve_tolerance_controller_not_found(self, monkeypatch):
        from modules.warehouse.controllers import T0101I
        import pytest
        from fastapi import HTTPException

        mock_svc = MagicMock()
        mock_svc.approve_tolerance.side_effect = ValueError("Pick list 999 not found")
        monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            T0101I.approve_tolerance(id=999, body={})
        assert exc_info.value.status_code == 404

