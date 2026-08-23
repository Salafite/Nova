import pytest
from unittest.mock import MagicMock, patch
from modules.warehouse.services.pick_list_service import PickListService


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
