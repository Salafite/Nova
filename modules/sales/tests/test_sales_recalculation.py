import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from modules.sales.services.sales_service import SalesOrderService
from modules.sales.controllers import T0012I


class TestSalesOrderRecalculation:
    def setup_method(self):
        self.mock_order_repo = MagicMock()
        self.mock_line_repo = MagicMock()
        self.mock_customer_repo = MagicMock()
        self.mock_inv_repo = MagicMock()
        self.mock_pl_repo = MagicMock()
        self.mock_pli_repo = MagicMock()
        self.mock_product_repo = MagicMock()

        self.service = SalesOrderService(
            repo=self.mock_order_repo,
            line_repo=self.mock_line_repo,
            customer_repo=self.mock_customer_repo,
            inv_repo=self.mock_inv_repo,
            pl_repo=self.mock_pl_repo,
            pli_repo=self.mock_pli_repo,
            product_repo=self.mock_product_repo,
        )

    def test_recalculate_positive_weight_variance(self):
        """Weighed amount is heavier than nominal (84.0kg vs 80.0kg nominal @ $15.00/kg)."""
        self.mock_order_repo.get.return_value = {
            'id': 10,
            'order_number': 'SO-00010',
            'customer_id': 100,
            'subtotal': 1200.0,
            'tax': 0.0,
            'grand_total': 1200.0,
            'freight_amount': 0.0,
            'discount_amount': 0.0,
            'status': 'Shipped',
        }
        self.mock_line_repo.list.return_value = [
            {
                'id': 101,
                'sales_order_id': 10,
                'product_id': 20,
                'product_name': 'Parmigiano Wheel 40kg',
                'qty': 2.0,
                'unit_price': 600.0,
                'line_total': 1200.0,
                'is_catch_weight': True,
                'pricing_uom_id': 1,
                'unit_price_pricing_uom': 15.0,
                'nominal_weight': 80.0,
                'catch_weight_actual': 84.0,
                'recalculated_total': None,
            }
        ]
        self.mock_pl_repo.list.return_value = []

        result = self.service.recalculate_order_catch_weight(10)

        assert result['is_catch_weight'] is True
        assert result['original_subtotal'] == 1200.0
        assert result['recalculated_subtotal'] == 1260.0  # 84.0 * 15.0
        assert result['weight_adjustment_amount'] == 60.0
        assert result['nominal_total_weight'] == 80.0
        assert result['actual_total_weight'] == 84.0
        assert result['grand_total'] == 1260.0

        # Verify line update
        self.mock_line_repo.update.assert_called_once_with(101, {
            'is_catch_weight': True,
            'catch_weight_actual': 84.0,
            'recalculated_total': 1260.0,
        }, conn=None)

        # Verify order header update
        self.mock_order_repo.update.assert_called_once_with(10, {
            'subtotal': 1260.0,
            'tax': 0.0,
            'grand_total': 1260.0,
        }, conn=None)

    def test_recalculate_negative_weight_variance(self):
        """Weighed amount is lighter than nominal (78.4kg vs 80.0kg nominal @ $15.00/kg)."""
        self.mock_order_repo.get.return_value = {
            'id': 11,
            'order_number': 'SO-00011',
            'customer_id': 100,
            'subtotal': 1200.0,
            'tax': 0.0,
            'grand_total': 1200.0,
            'freight_amount': 0.0,
            'discount_amount': 0.0,
            'status': 'Shipped',
        }
        self.mock_line_repo.list.return_value = [
            {
                'id': 102,
                'sales_order_id': 11,
                'product_id': 20,
                'product_name': 'Parmigiano Wheel 40kg',
                'qty': 2.0,
                'unit_price': 600.0,
                'line_total': 1200.0,
                'is_catch_weight': True,
                'pricing_uom_id': 1,
                'unit_price_pricing_uom': 15.0,
                'nominal_weight': 80.0,
                'catch_weight_actual': 78.4,
                'recalculated_total': None,
            }
        ]
        self.mock_pl_repo.list.return_value = []

        result = self.service.recalculate_order_catch_weight(11)

        assert result['is_catch_weight'] is True
        assert result['original_subtotal'] == 1200.0
        assert result['recalculated_subtotal'] == 1176.0  # 78.4 * 15.0
        assert result['weight_adjustment_amount'] == -24.0
        assert result['nominal_total_weight'] == 80.0
        assert result['actual_total_weight'] == 78.4
        assert result['grand_total'] == 1176.0

        self.mock_line_repo.update.assert_called_once_with(102, {
            'is_catch_weight': True,
            'catch_weight_actual': 78.4,
            'recalculated_total': 1176.0,
        }, conn=None)

    def test_recalculate_with_line_discount(self):
        """Actual catch weight with line discount subtracted from weight billing."""
        self.mock_order_repo.get.return_value = {
            'id': 12,
            'subtotal': 1150.0,
            'tax': 0.0,
            'grand_total': 1150.0,
        }
        self.mock_line_repo.list.return_value = [
            {
                'id': 103,
                'sales_order_id': 12,
                'product_id': 20,
                'qty': 2.0,
                'line_total': 1150.0,
                'discount': 50.0,
                'is_catch_weight': True,
                'unit_price_pricing_uom': 15.0,
                'nominal_weight': 80.0,
                'catch_weight_actual': 78.4,
            }
        ]
        self.mock_pl_repo.list.return_value = []

        result = self.service.recalculate_order_catch_weight(12)

        # 78.4 * 15.0 = 1176.0 - 50.0 discount = 1126.0
        assert result['recalculated_subtotal'] == 1126.0
        assert result['weight_adjustment_amount'] == -24.0  # (1126 - 1150)
        assert result['grand_total'] == 1126.0

    def test_recalculate_sourcing_actual_weight_from_pick_list_items(self):
        """When sales line catch_weight_actual is None, sources weight from pick list items."""
        self.mock_order_repo.get.return_value = {
            'id': 13,
            'subtotal': 1200.0,
            'tax': 0.0,
            'grand_total': 1200.0,
        }
        self.mock_line_repo.list.return_value = [
            {
                'id': 104,
                'sales_order_id': 13,
                'product_id': 20,
                'line_total': 1200.0,
                'is_catch_weight': True,
                'unit_price_pricing_uom': 15.0,
                'nominal_weight': 80.0,
                'catch_weight_actual': None,  # Not populated on line yet
            }
        ]
        self.mock_pl_repo.list.return_value = [{'id': 501, 'sales_order_id': 13}]
        self.mock_pli_repo.list.return_value = [
            {
                'id': 1,
                'pick_list_id': 501,
                'sales_order_line_id': 104,
                'catch_weight_actual': 79.2,
                'nominal_weight': 80.0,
            }
        ]

        result = self.service.recalculate_order_catch_weight(13)

        assert result['actual_total_weight'] == 79.2
        assert result['recalculated_subtotal'] == 1188.0  # 79.2 * 15.0
        assert result['weight_adjustment_amount'] == -12.0
        self.mock_line_repo.update.assert_called_once_with(104, {
            'is_catch_weight': True,
            'catch_weight_actual': 79.2,
            'recalculated_total': 1188.0,
        }, conn=None)

    def test_recalculate_multiple_pick_list_items_aggregated(self):
        """Multiple pick list items (e.g. split across lots) aggregated for a single line."""
        self.mock_order_repo.get.return_value = {
            'id': 14,
            'subtotal': 1200.0,
            'tax': 0.0,
            'grand_total': 1200.0,
        }
        self.mock_line_repo.list.return_value = [
            {
                'id': 105,
                'sales_order_id': 14,
                'product_id': 20,
                'line_total': 1200.0,
                'is_catch_weight': True,
                'unit_price_pricing_uom': 15.0,
                'nominal_weight': 80.0,
                'catch_weight_actual': None,
            }
        ]
        self.mock_pl_repo.list.return_value = [{'id': 502, 'sales_order_id': 14}]
        self.mock_pli_repo.list.return_value = [
            {
                'id': 1,
                'pick_list_id': 502,
                'sales_order_line_id': 105,
                'catch_weight_actual': 39.5,
                'nominal_weight': 40.0,
            },
            {
                'id': 2,
                'pick_list_id': 502,
                'sales_order_line_id': 105,
                'catch_weight_actual': 39.1,
                'nominal_weight': 40.0,
            },
        ]

        result = self.service.recalculate_order_catch_weight(14)

        assert result['actual_total_weight'] == 78.6  # 39.5 + 39.1
        assert result['recalculated_subtotal'] == 1179.0  # 78.6 * 15.0
        assert result['weight_adjustment_amount'] == -21.0

    def test_recalculate_mixed_order_catch_weight_and_standard_lines(self):
        """Mixed order: 1 catch-weight item + 1 standard item."""
        self.mock_order_repo.get.return_value = {
            'id': 15,
            'subtotal': 1450.0,  # 1200 + 250
            'tax': 0.0,
            'grand_total': 1450.0,
        }
        self.mock_line_repo.list.return_value = [
            {
                'id': 106,
                'sales_order_id': 15,
                'product_name': 'Cheese Wheel',
                'line_total': 1200.0,
                'is_catch_weight': True,
                'unit_price_pricing_uom': 15.0,
                'nominal_weight': 80.0,
                'catch_weight_actual': 82.0,
            },
            {
                'id': 107,
                'sales_order_id': 15,
                'product_name': 'Standard Olive Oil Box',
                'line_total': 250.0,
                'is_catch_weight': False,
                'catch_weight_actual': None,
            }
        ]
        self.mock_pl_repo.list.return_value = []

        result = self.service.recalculate_order_catch_weight(15)

        assert result['is_catch_weight'] is True
        assert result['original_subtotal'] == 1450.0
        assert result['recalculated_subtotal'] == 1480.0  # (82.0 * 15 = 1230) + 250
        assert result['weight_adjustment_amount'] == 30.0
        assert result['nominal_total_weight'] == 80.0
        assert result['actual_total_weight'] == 82.0
        assert result['grand_total'] == 1480.0

    def test_recalculate_tax_adjusted_proportionally(self):
        """Tax is recalculated proportionally when subtotal shifts due to catch weight."""
        self.mock_order_repo.get.return_value = {
            'id': 16,
            'subtotal': 1000.0,
            'tax': 100.0,  # 10% tax
            'grand_total': 1100.0,
            'freight_amount': 20.0,
            'discount_amount': 10.0,
        }
        self.mock_line_repo.list.return_value = [
            {
                'id': 108,
                'sales_order_id': 16,
                'line_total': 1000.0,
                'is_catch_weight': True,
                'unit_price_pricing_uom': 10.0,
                'nominal_weight': 100.0,
                'catch_weight_actual': 105.0,  # +5%
            }
        ]
        self.mock_pl_repo.list.return_value = []

        result = self.service.recalculate_order_catch_weight(16)

        assert result['recalculated_subtotal'] == 1050.0  # 105.0 * 10
        assert result['tax'] == 105.0  # 10% of 1050
        # 1050 (subtotal) + 105 (tax) + 20 (freight) - 10 (discount) = 1165.0
        assert result['grand_total'] == 1165.0

    def test_recalculate_fallback_price_ratio_when_no_unit_price_pricing_uom(self):
        """When unit_price_pricing_uom is None, derives effective price per weight from line_total/nominal_weight."""
        self.mock_order_repo.get.return_value = {
            'id': 17,
            'subtotal': 1000.0,
            'tax': 0.0,
            'grand_total': 1000.0,
        }
        self.mock_line_repo.list.return_value = [
            {
                'id': 109,
                'sales_order_id': 17,
                'line_total': 1000.0,
                'is_catch_weight': True,
                'unit_price_pricing_uom': None,
                'nominal_weight': 50.0,  # $1000 / 50kg = $20/kg
                'catch_weight_actual': 52.0,  # 52kg * $20 = $1040
            }
        ]
        self.mock_pl_repo.list.return_value = []

        result = self.service.recalculate_order_catch_weight(17)

        assert result['recalculated_subtotal'] == 1040.0
        assert result['weight_adjustment_amount'] == 40.0

    def test_recalculate_no_catch_weight_items(self):
        """Regular non-catch-weight order is unaffected."""
        self.mock_order_repo.get.return_value = {
            'id': 18,
            'subtotal': 500.0,
            'tax': 25.0,
            'grand_total': 525.0,
        }
        self.mock_line_repo.list.return_value = [
            {
                'id': 110,
                'sales_order_id': 18,
                'line_total': 500.0,
                'is_catch_weight': False,
                'catch_weight_actual': None,
            }
        ]
        self.mock_pl_repo.list.return_value = []

        result = self.service.recalculate_order_catch_weight(18)

        assert result['is_catch_weight'] is False
        assert result['recalculated_subtotal'] == 500.0
        assert result['weight_adjustment_amount'] == 0.0
        assert result['nominal_total_weight'] is None
        assert result['actual_total_weight'] is None
        assert result['grand_total'] == 525.0

    def test_recalculate_order_not_found_raises(self):
        self.mock_order_repo.get.return_value = None
        with pytest.raises(ValueError, match="Sales order 999 not found"):
            self.service.recalculate_order_catch_weight(999)


class TestSalesOrderDeliveryAndInvoicing:
    def setup_method(self):
        self.mock_order_repo = MagicMock()
        self.mock_line_repo = MagicMock()
        self.mock_customer_repo = MagicMock()
        self.mock_inv_repo = MagicMock()
        self.mock_pl_repo = MagicMock()
        self.mock_pli_repo = MagicMock()

        self.service = SalesOrderService(
            repo=self.mock_order_repo,
            line_repo=self.mock_line_repo,
            customer_repo=self.mock_customer_repo,
            inv_repo=self.mock_inv_repo,
            pl_repo=self.mock_pl_repo,
            pli_repo=self.mock_pli_repo,
        )

    def test_order_delivered_triggers_recalculation_and_invoicing(self):
        """Order delivery recalculates catch-weight lines, creates invoice, and updates customer balance."""
        order_data = {
            'id': 50,
            'order_number': 'SO-00050',
            'customer_id': 200,
            'subtotal': 1200.0,
            'tax': 0.0,
            'grand_total': 1200.0,
            'status': 'Shipped',
            'order_date': date(2026, 8, 23),
        }
        self.mock_order_repo.get.side_effect = [
            order_data,  # for status check
            order_data,  # for recalculation
            dict(order_data, subtotal=1176.0, grand_total=1176.0),  # after recalculation in _create_invoice
        ]
        self.mock_line_repo.list.return_value = [
            {
                'id': 201,
                'sales_order_id': 50,
                'product_name': 'Parmigiano Wheel',
                'line_total': 1200.0,
                'is_catch_weight': True,
                'unit_price_pricing_uom': 15.0,
                'nominal_weight': 80.0,
                'catch_weight_actual': 78.4,
            }
        ]
        self.mock_pl_repo.list.return_value = []
        self.mock_customer_repo.get.return_value = {
            'id': 200,
            'name': 'Gourmet Market',
            'balance': 500.0,
            'credit_limit': 5000.0,
        }

        with patch.object(self.service, '_generate_invoice_number', return_value='INV-00050'):
            self.service.update(50, {'status': 'Delivered'})

        # Verify invoice created with catch-weight aggregates and adjusted total
        self.mock_inv_repo.create.assert_called_once()
        inv_args, inv_kwargs = self.mock_inv_repo.create.call_args
        inv_payload = inv_args[0]

        assert inv_payload['invoice_number'] == 'INV-00050'
        assert inv_payload['sales_order_id'] == 50
        assert inv_payload['partner_id'] == 200
        assert inv_payload['total_amount'] == 1176.0  # Recalculated total
        assert inv_payload['is_catch_weight'] is True
        assert inv_payload['nominal_total_weight'] == 80.0
        assert inv_payload['actual_total_weight'] == 78.4
        assert inv_payload['weight_adjustment_amount'] == -24.0
        assert 'Catch-weight adjustment: -24.00' in inv_payload['notes']

        # Verify customer balance updated with recalculated grand total (500 + 1176 = 1676)
        self.mock_customer_repo.update.assert_called_once()
        cust_args, cust_kwargs = self.mock_customer_repo.update.call_args
        assert cust_args[0] == 200
        assert cust_args[1]['balance'] == 1676.0

    def test_order_creation_inherits_customer_payment_term_when_omitted(self):
        """When payment_term_id is not passed, order inherits customer's payment_term_id."""
        mock_payment_term_repo = MagicMock()
        service = SalesOrderService(
            repo=self.mock_order_repo,
            customer_repo=self.mock_customer_repo,
            payment_term_repo=mock_payment_term_repo,
        )
        self.mock_customer_repo.get.return_value = {
            'id': 200,
            'name': 'Boutique Foods',
            'payment_term_id': 5,
            'balance': 0.0,
            'credit_limit': 10000.0,
        }
        self.mock_order_repo.create.return_value = {'id': 99, 'payment_term_id': 5}

        payload = {'customer_id': 200, 'subtotal': 500.0}
        service.create(payload)

        assert payload['payment_term_id'] == 5
        self.mock_order_repo.create.assert_called_once_with(payload)

    def test_order_creation_preserves_explicit_payment_term(self):
        """When payment_term_id is explicitly passed, customer's payment term is not applied."""
        mock_payment_term_repo = MagicMock()
        service = SalesOrderService(
            repo=self.mock_order_repo,
            customer_repo=self.mock_customer_repo,
            payment_term_repo=mock_payment_term_repo,
        )
        self.mock_customer_repo.get.return_value = {
            'id': 200,
            'name': 'Boutique Foods',
            'payment_term_id': 5,
            'balance': 0.0,
            'credit_limit': 10000.0,
        }
        self.mock_order_repo.create.return_value = {'id': 99, 'payment_term_id': 2}

        payload = {'customer_id': 200, 'payment_term_id': 2, 'subtotal': 500.0}
        service.create(payload)

        assert payload['payment_term_id'] == 2
        self.mock_order_repo.create.assert_called_once_with(payload)

    def test_order_creation_falls_back_to_default_payment_term(self):
        """When customer has no payment term, order falls back to active default payment term."""
        mock_payment_term_repo = MagicMock()
        mock_payment_term_repo.list.return_value = [{'id': 1, 'code': 'NET_30', 'is_default': True}]
        service = SalesOrderService(
            repo=self.mock_order_repo,
            customer_repo=self.mock_customer_repo,
            payment_term_repo=mock_payment_term_repo,
        )
        self.mock_customer_repo.get.return_value = {
            'id': 200,
            'name': 'Boutique Foods',
            'payment_term_id': None,
            'balance': 0.0,
            'credit_limit': 10000.0,
        }
        self.mock_order_repo.create.return_value = {'id': 99, 'payment_term_id': 1}

        payload = {'customer_id': 200, 'subtotal': 500.0}
        service.create(payload)

        assert payload['payment_term_id'] == 1
        mock_payment_term_repo.list.assert_called_once_with(filters={'is_default': True, 'is_active': True}, limit=1, conn=None)

    def test_order_delivery_computes_2_10_net_30_due_date_and_early_discount(self):
        """Order delivery with 2/10 Net 30 terms computes due date (+30d), discount deadline (+10d), and discount amount."""
        mock_payment_term_repo = MagicMock()
        service = SalesOrderService(
            repo=self.mock_order_repo,
            line_repo=self.mock_line_repo,
            customer_repo=self.mock_customer_repo,
            inv_repo=self.mock_inv_repo,
            pl_repo=self.mock_pl_repo,
            pli_repo=self.mock_pli_repo,
            payment_term_repo=mock_payment_term_repo,
        )

        order_data = {
            'id': 60,
            'order_number': 'SO-00060',
            'customer_id': 300,
            'payment_term_id': 4,
            'subtotal': 2000.0,
            'tax': 0.0,
            'grand_total': 2000.0,
            'status': 'Shipped',
            'order_date': date(2026, 8, 1),
        }
        self.mock_order_repo.get.side_effect = [
            order_data,
            order_data,
            order_data,
        ]
        self.mock_line_repo.list.return_value = []
        self.mock_pl_repo.list.return_value = []
        self.mock_customer_repo.get.return_value = {
            'id': 300,
            'name': 'Artisan Bakery',
            'balance': 0.0,
            'payment_term_id': 4,
        }
        mock_payment_term_repo.get.return_value = {
            'id': 4,
            'name': '2/10 Net 30',
            'code': '2_10_NET_30',
            'due_days': 30,
            'discount_percentage': 2.0,
            'discount_days': 10,
            'is_active': True,
        }

        with patch.object(service, '_generate_invoice_number', return_value='INV-00060'):
            service.update(60, {'status': 'Delivered'})

        self.mock_inv_repo.create.assert_called_once()
        inv_payload = self.mock_inv_repo.create.call_args[0][0]

        assert inv_payload['invoice_number'] == 'INV-00060'
        assert inv_payload['payment_term_id'] == 4
        assert inv_payload['issue_date'] == date(2026, 8, 1)
        assert inv_payload['due_date'] == date(2026, 8, 31)  # 2026-08-01 + 30 days
        assert inv_payload['discount_due_date'] == date(2026, 8, 11)  # 2026-08-01 + 10 days
        assert inv_payload['discount_percentage'] == 2.0
        assert inv_payload['discount_days'] == 10
        assert inv_payload['early_discount_amount'] == 40.0  # 2% of 2000.0

    def test_order_delivery_computes_cod_due_date(self):
        """Order delivery with COD terms sets due date equal to delivery date, discount_due_date to None."""
        mock_payment_term_repo = MagicMock()
        service = SalesOrderService(
            repo=self.mock_order_repo,
            line_repo=self.mock_line_repo,
            customer_repo=self.mock_customer_repo,
            inv_repo=self.mock_inv_repo,
            pl_repo=self.mock_pl_repo,
            pli_repo=self.mock_pli_repo,
            payment_term_repo=mock_payment_term_repo,
        )

        order_data = {
            'id': 61,
            'order_number': 'SO-00061',
            'customer_id': 301,
            'payment_term_id': 2,
            'subtotal': 500.0,
            'tax': 0.0,
            'grand_total': 500.0,
            'status': 'Shipped',
            'order_date': date(2026, 8, 15),
        }
        self.mock_order_repo.get.side_effect = [
            order_data,
            order_data,
            order_data,
        ]
        self.mock_line_repo.list.return_value = []
        self.mock_pl_repo.list.return_value = []
        self.mock_customer_repo.get.return_value = {
            'id': 301,
            'name': 'Cash Cafe',
            'balance': 0.0,
            'payment_term_id': 2,
        }
        mock_payment_term_repo.get.return_value = {
            'id': 2,
            'name': 'Cash on Delivery (COD)',
            'code': 'COD',
            'due_days': 0,
            'discount_percentage': 0.0,
            'discount_days': 0,
            'is_active': True,
        }

        with patch.object(service, '_generate_invoice_number', return_value='INV-00061'):
            service.update(61, {'status': 'Delivered'})

        self.mock_inv_repo.create.assert_called_once()
        inv_payload = self.mock_inv_repo.create.call_args[0][0]

        assert inv_payload['payment_term_id'] == 2
        assert inv_payload['issue_date'] == date(2026, 8, 15)
        assert inv_payload['due_date'] == date(2026, 8, 15)  # COD = due immediately (0 days)
        assert inv_payload['discount_due_date'] is None
        assert inv_payload['discount_percentage'] == 0.0
        assert inv_payload['early_discount_amount'] == 0.0


class TestSalesOrderControllerEndpoints:
    def test_recalculate_catch_weight_controller_endpoint(self, monkeypatch):
        mock_svc = MagicMock()
        mock_svc.get.return_value = {'id': 100, 'order_number': 'SO-00100'}
        mock_svc.recalculate_order_catch_weight.return_value = {
            'order_id': 100,
            'is_catch_weight': True,
            'original_subtotal': 1200.0,
            'recalculated_subtotal': 1176.0,
            'weight_adjustment_amount': -24.0,
            'nominal_total_weight': 80.0,
            'actual_total_weight': 78.4,
            'grand_total': 1176.0,
        }
        monkeypatch.setattr(T0012I, 'service', mock_svc)

        result = T0012I.recalculate_order_catch_weight(id=100)

        assert result['is_catch_weight'] is True
        assert result['recalculated_subtotal'] == 1176.0
        assert result['weight_adjustment_amount'] == -24.0
        mock_svc.recalculate_order_catch_weight.assert_called_once_with(100)

    def test_recalculate_preview_controller_endpoint(self, monkeypatch):
        mock_svc = MagicMock()
        mock_svc.get.return_value = {'id': 100, 'order_number': 'SO-00100'}
        mock_svc.recalculate_order_catch_weight.return_value = {
            'order_id': 100,
            'is_catch_weight': True,
            'recalculated_subtotal': 1260.0,
            'weight_adjustment_amount': 60.0,
        }
        monkeypatch.setattr(T0012I, 'service', mock_svc)

        result = T0012I.preview_order_catch_weight_recalculation(id=100)
        assert result['weight_adjustment_amount'] == 60.0
        mock_svc.recalculate_order_catch_weight.assert_called_once_with(100)

    def test_recalculate_not_found_raises_404(self, monkeypatch):
        mock_svc = MagicMock()
        mock_svc.get.return_value = None
        monkeypatch.setattr(T0012I, 'service', mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            T0012I.recalculate_order_catch_weight(id=999)
        assert exc_info.value.status_code == 404
