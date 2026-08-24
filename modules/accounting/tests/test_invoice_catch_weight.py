import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from modules.accounting.services.invoice_service import InvoiceService
from modules.accounting.controllers import T0090I


class TestInvoiceCatchWeightService:
    def setup_method(self):
        self.mock_inv_repo = MagicMock()
        self.mock_customer_repo = MagicMock()
        self.mock_order_repo = MagicMock()
        self.mock_line_repo = MagicMock()

        self.service = InvoiceService(
            repo=self.mock_inv_repo,
            customer_repo=self.mock_customer_repo,
            order_repo=self.mock_order_repo,
            line_repo=self.mock_line_repo,
        )

    def test_calculate_catch_weight_summary_positive_variance(self):
        """Catch-weight lines with positive weight variance (+4.0kg @ $15.00/kg = +$60.00)."""
        lines = [
            {
                'id': 1,
                'line_total': 1200.0,
                'is_catch_weight': True,
                'nominal_weight': 80.0,
                'catch_weight_actual': 84.0,
                'unit_price_pricing_uom': 15.0,
                'discount': 0.0,
            }
        ]

        summary = self.service.calculate_catch_weight_summary(lines)

        assert summary['is_catch_weight'] is True
        assert summary['nominal_total_weight'] == 80.0
        assert summary['actual_total_weight'] == 84.0
        assert summary['original_subtotal'] == 1200.0
        assert summary['recalculated_subtotal'] == 1260.0
        assert summary['weight_adjustment_amount'] == 60.0
        assert summary['lines'][0]['recalculated_total'] == 1260.0

    def test_calculate_catch_weight_summary_negative_variance(self):
        """Catch-weight lines with negative weight variance (-1.6kg @ $15.00/kg = -$24.00)."""
        lines = [
            {
                'id': 2,
                'line_total': 1200.0,
                'is_catch_weight': True,
                'nominal_weight': 80.0,
                'catch_weight_actual': 78.4,
                'unit_price_pricing_uom': 15.0,
                'discount': 0.0,
            }
        ]

        summary = self.service.calculate_catch_weight_summary(lines)

        assert summary['is_catch_weight'] is True
        assert summary['nominal_total_weight'] == 80.0
        assert summary['actual_total_weight'] == 78.4
        assert summary['original_subtotal'] == 1200.0
        assert summary['recalculated_subtotal'] == 1176.0
        assert summary['weight_adjustment_amount'] == -24.0
        assert summary['lines'][0]['recalculated_total'] == 1176.0

    def test_calculate_catch_weight_summary_with_line_discount(self):
        """Catch-weight calculation honoring line discounts."""
        lines = [
            {
                'id': 3,
                'line_total': 1150.0,
                'is_catch_weight': True,
                'nominal_weight': 80.0,
                'catch_weight_actual': 80.0,
                'unit_price_pricing_uom': 15.0,
                'discount': 50.0,
            }
        ]

        summary = self.service.calculate_catch_weight_summary(lines)

        # 80.0 * 15.0 = 1200.0 - 50 = 1150.0
        assert summary['recalculated_subtotal'] == 1150.0
        assert summary['weight_adjustment_amount'] == 0.0

    def test_calculate_catch_weight_summary_non_catch_weight(self):
        """Regular non-catch-weight lines."""
        lines = [
            {
                'id': 4,
                'line_total': 300.0,
                'is_catch_weight': False,
                'nominal_weight': None,
                'catch_weight_actual': None,
            }
        ]

        summary = self.service.calculate_catch_weight_summary(lines)

        assert summary['is_catch_weight'] is False
        assert summary['nominal_total_weight'] is None
        assert summary['actual_total_weight'] is None
        assert summary['original_subtotal'] == 300.0
        assert summary['recalculated_subtotal'] == 300.0
        assert summary['weight_adjustment_amount'] == 0.0

    def test_create_from_order_with_catch_weight_and_customer_balance(self):
        """Create invoice from order payload and update customer balance."""
        order = {
            'id': 10,
            'order_number': 'SO-00010',
            'customer_id': 100,
            'sales_rep_id': 5,
            'order_date': date(2026, 8, 23),
            'grand_total': 1260.0,
            'freight_amount': 0.0,
            'discount_amount': 0.0,
            'is_catch_weight': True,
        }
        recalc_summary = {
            'is_catch_weight': True,
            'nominal_total_weight': 80.0,
            'actual_total_weight': 84.0,
            'weight_adjustment_amount': 60.0,
        }
        self.mock_customer_repo.get.return_value = {
            'id': 100,
            'name': 'Artisan Cheese Shop',
            'balance': 400.0,
        }
        self.mock_inv_repo.create.return_value = {
            'id': 1,
            'invoice_number': 'INV-00001',
            'total_amount': 1260.0,
        }

        with patch('modules.accounting.services.invoice_service.generate_invoice_number', return_value='INV-00001'):
            result = self.service.create_from_order(order, recalculation_summary=recalc_summary, update_customer_balance=True)

        self.mock_inv_repo.create.assert_called_once()
        inv_payload = self.mock_inv_repo.create.call_args[0][0]
        assert inv_payload['invoice_number'] == 'INV-00001'
        assert inv_payload['total_amount'] == 1260.0
        assert inv_payload['is_catch_weight'] is True
        assert inv_payload['nominal_total_weight'] == 80.0
        assert inv_payload['actual_total_weight'] == 84.0
        assert inv_payload['weight_adjustment_amount'] == 60.0
        assert 'Catch-weight adjustment: +60.00' in inv_payload['notes']

        # Verify customer balance updated (400 + 1260 = 1660)
        self.mock_customer_repo.update.assert_called_once_with(100, {'balance': 1660.0}, conn=None)

    def test_recalculate_and_invoice_order_end_to_end(self):
        """Recalculate order from line items, update order header, create invoice, and update customer balance."""
        self.mock_order_repo.get.return_value = {
            'id': 20,
            'order_number': 'SO-00020',
            'customer_id': 200,
            'subtotal': 1000.0,
            'tax': 100.0,
            'grand_total': 1100.0,
            'freight_amount': 0.0,
            'discount_amount': 0.0,
            'order_date': date(2026, 8, 23),
        }
        self.mock_line_repo.list.return_value = [
            {
                'id': 501,
                'sales_order_id': 20,
                'product_name': 'Aged Gouda Wheel',
                'line_total': 1000.0,
                'is_catch_weight': True,
                'unit_price_pricing_uom': 20.0,
                'nominal_weight': 50.0,
                'catch_weight_actual': 53.0,  # 53kg * $20 = $1060 (+60 subtotal)
                'discount': 0.0,
            }
        ]
        self.mock_customer_repo.get.return_value = {
            'id': 200,
            'name': 'Gourmet Deli',
            'balance': 0.0,
        }
        self.mock_inv_repo.create.return_value = {
            'id': 2,
            'invoice_number': 'INV-00002',
            'total_amount': 1166.0,  # 1060 subtotal + 106 tax (10%)
        }

        with patch('modules.accounting.services.invoice_service.generate_invoice_number', return_value='INV-00002'):
            result = self.service.recalculate_and_invoice_order(20)

        # Verify order header updated: subtotal 1060, tax 106, grand_total 1166
        self.mock_order_repo.update.assert_called_once_with(20, {
            'subtotal': 1060.0,
            'tax': 106.0,
            'grand_total': 1166.0,
        }, conn=None)

        # Verify line updated
        self.mock_line_repo.update.assert_called_once_with(501, {
            'is_catch_weight': True,
            'recalculated_total': 1060.0,
            'catch_weight_actual': 53.0,
        }, conn=None)

        # Verify invoice created
        self.mock_inv_repo.create.assert_called_once()
        inv_payload = self.mock_inv_repo.create.call_args[0][0]
        assert inv_payload['total_amount'] == 1166.0
        assert inv_payload['weight_adjustment_amount'] == 60.0
        assert inv_payload['nominal_total_weight'] == 50.0
        assert inv_payload['actual_total_weight'] == 53.0

        # Verify customer balance updated
        self.mock_customer_repo.update.assert_called_once_with(200, {'balance': 1166.0}, conn=None)

    def test_get_catch_weight_breakdown(self):
        """Retrieve breakdown for an invoice."""
        self.mock_inv_repo.get.return_value = {
            'id': 5,
            'invoice_number': 'INV-00005',
            'sales_order_id': 30,
            'is_catch_weight': True,
            'nominal_total_weight': 40.0,
            'actual_total_weight': 42.5,
            'weight_adjustment_amount': 25.0,
            'total_amount': 425.0,
        }
        self.mock_line_repo.list.return_value = [
            {
                'id': 1,
                'sales_order_id': 30,
                'product_name': 'Cheddar Block',
                'line_total': 400.0,
                'recalculated_total': 425.0,
                'is_catch_weight': True,
            }
        ]

        breakdown = self.service.get_catch_weight_breakdown(5)

        assert breakdown['invoice_id'] == 5
        assert breakdown['invoice_number'] == 'INV-00005'
        assert breakdown['is_catch_weight'] is True
        assert breakdown['nominal_total_weight'] == 40.0
        assert breakdown['actual_total_weight'] == 42.5
        assert breakdown['weight_adjustment_amount'] == 25.0
        assert len(breakdown['lines']) == 1


class TestInvoiceCatchWeightController:
    def test_from_order_endpoint(self, monkeypatch):
        mock_svc = MagicMock()
        mock_svc.recalculate_and_invoice_order.return_value = {
            'id': 1,
            'invoice_number': 'INV-00001',
            'total_amount': 1260.0,
            'is_catch_weight': True,
        }
        monkeypatch.setattr(T0090I, 'service', mock_svc)

        result = T0090I.create_invoice_from_order(order_id=10)

        assert result['invoice_number'] == 'INV-00001'
        assert result['is_catch_weight'] is True
        mock_svc.recalculate_and_invoice_order.assert_called_once_with(10)

    def test_catch_weight_breakdown_endpoint(self, monkeypatch):
        mock_svc = MagicMock()
        mock_svc.get_catch_weight_breakdown.return_value = {
            'invoice_id': 1,
            'is_catch_weight': True,
            'nominal_total_weight': 80.0,
            'actual_total_weight': 84.0,
        }
        monkeypatch.setattr(T0090I, 'service', mock_svc)

        result = T0090I.get_invoice_catch_weight_breakdown(id=1)

        assert result['is_catch_weight'] is True
        assert result['actual_total_weight'] == 84.0
        mock_svc.get_catch_weight_breakdown.assert_called_once_with(1)

    def test_from_order_not_found_raises_404(self, monkeypatch):
        mock_svc = MagicMock()
        mock_svc.recalculate_and_invoice_order.side_effect = ValueError("Sales order 999 not found")
        monkeypatch.setattr(T0090I, 'service', mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            T0090I.create_invoice_from_order(order_id=999)
        assert exc_info.value.status_code == 404
