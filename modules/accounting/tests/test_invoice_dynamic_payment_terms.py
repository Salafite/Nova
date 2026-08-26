import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from modules.accounting.services.invoice_service import InvoiceService
from modules.accounting.controllers import T0090I


class TestInvoiceServiceDirectCreation:
    def setup_method(self):
        self.mock_inv_repo = MagicMock()
        self.mock_customer_repo = MagicMock()
        self.mock_order_repo = MagicMock()
        self.mock_line_repo = MagicMock()
        self.mock_payment_term_repo = MagicMock()

        self.service = InvoiceService(
            repo=self.mock_inv_repo,
            customer_repo=self.mock_customer_repo,
            order_repo=self.mock_order_repo,
            line_repo=self.mock_line_repo,
            payment_term_repo=self.mock_payment_term_repo,
        )

    def test_create_invoice_with_payment_term_2_10_net_30(self):
        """Create invoice with explicit 2/10 Net 30 payment term calculates due date and early discount."""
        self.mock_payment_term_repo.get.return_value = {
            'id': 5,
            'name': '2/10 Net 30',
            'code': '2_10_NET_30',
            'due_days': 30,
            'discount_percentage': 2.0,
            'discount_days': 10,
            'is_active': True,
        }
        self.mock_inv_repo.create.side_effect = lambda payload, conn=None: dict(payload, id=1)

        payload = {
            'partner_id': 10,
            'payment_term_id': 5,
            'issue_date': date(2026, 8, 1),
            'total_amount': 1000.0,
        }

        with patch('modules.accounting.services.invoice_service.generate_invoice_number', return_value='INV-00001'):
            created = self.service.create(payload)

        assert created['invoice_number'] == 'INV-00001'
        assert created['payment_term_id'] == 5
        assert created['issue_date'] == date(2026, 8, 1)
        assert created['due_date'] == date(2026, 8, 31)
        assert created['discount_due_date'] == date(2026, 8, 11)
        assert created['discount_percentage'] == 2.0
        assert created['discount_days'] == 10
        assert created['early_discount_amount'] == 20.0  # 2% of 1000.0

    def test_create_invoice_inherits_customer_payment_term(self):
        """Create invoice without payment_term_id inherits customer payment term (Net 15)."""
        self.mock_customer_repo.get.return_value = {
            'id': 20,
            'name': 'Quick Pay Client',
            'payment_term_id': 3,
        }
        self.mock_payment_term_repo.get.return_value = {
            'id': 3,
            'name': 'Net 15',
            'code': 'NET_15',
            'due_days': 15,
            'discount_percentage': 0.0,
            'discount_days': 0,
            'is_active': True,
        }
        self.mock_inv_repo.create.side_effect = lambda payload, conn=None: dict(payload, id=2)

        payload = {
            'partner_id': 20,
            'issue_date': date(2026, 8, 10),
            'total_amount': 500.0,
        }

        with patch('modules.accounting.services.invoice_service.generate_invoice_number', return_value='INV-00002'):
            created = self.service.create(payload)

        assert created['payment_term_id'] == 3
        assert created['issue_date'] == date(2026, 8, 10)
        assert created['due_date'] == date(2026, 8, 25)
        assert created['discount_due_date'] is None
        assert created['discount_percentage'] == 0.0
        assert created['discount_days'] == 0
        assert created['early_discount_amount'] == 0.0

    def test_create_invoice_cod_term(self):
        """Create invoice with COD term sets due_date equal to issue_date."""
        self.mock_payment_term_repo.get.return_value = {
            'id': 2,
            'name': 'Cash on Delivery (COD)',
            'code': 'COD',
            'due_days': 0,
            'discount_percentage': 0.0,
            'discount_days': 0,
            'is_active': True,
        }
        self.mock_inv_repo.create.side_effect = lambda payload, conn=None: dict(payload, id=3)

        payload = {
            'partner_id': 30,
            'payment_term_id': 2,
            'issue_date': date(2026, 8, 15),
            'total_amount': 750.0,
        }

        with patch('modules.accounting.services.invoice_service.generate_invoice_number', return_value='INV-00003'):
            created = self.service.create(payload)

        assert created['payment_term_id'] == 2
        assert created['due_date'] == date(2026, 8, 15)
        assert created['discount_due_date'] is None

    def test_create_invoice_preserves_explicit_due_date(self):
        """Explicit due_date and early discount details are preserved if already specified in payload."""
        self.mock_payment_term_repo.get.return_value = {
            'id': 1,
            'name': 'Net 30',
            'due_days': 30,
            'discount_percentage': 0.0,
            'discount_days': 0,
        }
        self.mock_inv_repo.create.side_effect = lambda payload, conn=None: dict(payload, id=4)

        payload = {
            'partner_id': 10,
            'payment_term_id': 1,
            'issue_date': date(2026, 8, 1),
            'due_date': date(2026, 8, 20),  # Explicitly different
            'total_amount': 1000.0,
        }

        with patch('modules.accounting.services.invoice_service.generate_invoice_number', return_value='INV-00004'):
            created = self.service.create(payload)

        assert created['due_date'] == date(2026, 8, 20)

    def test_create_invoice_resolves_term_from_sales_order_if_unspecified(self):
        """If payment_term_id is not in payload but sales_order_id is provided, term is resolved from the order."""
        self.mock_order_repo.get.return_value = {
            'id': 100,
            'payment_term_id': 4,  # Net 60
        }
        self.mock_payment_term_repo.get.return_value = {
            'id': 4,
            'name': 'Net 60',
            'code': 'NET_60',
            'due_days': 60,
            'discount_percentage': 0.0,
            'discount_days': 0,
            'is_active': True,
        }
        self.mock_inv_repo.create.side_effect = lambda payload, conn=None: dict(payload, id=5)

        payload = {
            'partner_id': 10,
            'sales_order_id': 100,
            'issue_date': date(2026, 8, 1),
            'total_amount': 1200.0,
        }

        with patch('modules.accounting.services.invoice_service.generate_invoice_number', return_value='INV-00005'):
            created = self.service.create(payload)

        assert created['payment_term_id'] == 4
        assert created['due_date'] == date(2026, 9, 30)


class TestInvoiceServiceCreateFromOrder:
    def setup_method(self):
        self.mock_inv_repo = MagicMock()
        self.mock_customer_repo = MagicMock()
        self.mock_order_repo = MagicMock()
        self.mock_line_repo = MagicMock()
        self.mock_payment_term_repo = MagicMock()

        self.service = InvoiceService(
            repo=self.mock_inv_repo,
            customer_repo=self.mock_customer_repo,
            order_repo=self.mock_order_repo,
            line_repo=self.mock_line_repo,
            payment_term_repo=self.mock_payment_term_repo,
        )

    def test_create_from_order_with_2_10_net_30(self):
        """Create invoice from order with 2/10 Net 30 computes dynamic due date and discount cutoff."""
        order = {
            'id': 50,
            'order_number': 'SO-00050',
            'customer_id': 105,
            'sales_rep_id': 2,
            'order_date': date(2026, 8, 10),
            'grand_total': 2000.0,
            'freight_amount': 50.0,
            'discount_amount': 0.0,
            'payment_term_id': 5,
        }
        self.mock_payment_term_repo.get.return_value = {
            'id': 5,
            'name': '2/10 Net 30',
            'code': '2_10_NET_30',
            'due_days': 30,
            'discount_percentage': 2.0,
            'discount_days': 10,
            'is_active': True,
        }
        self.mock_customer_repo.get.return_value = {
            'id': 105,
            'name': 'Alpha Corp',
            'balance': 100.0,
        }
        self.mock_inv_repo.create.side_effect = lambda payload, conn=None: dict(payload, id=500)

        with patch('modules.accounting.services.invoice_service.generate_invoice_number', return_value='INV-00050'):
            invoice = self.service.create_from_order(order, update_customer_balance=True)

        assert invoice['invoice_number'] == 'INV-00050'
        assert invoice['partner_id'] == 105
        assert invoice['sales_order_id'] == 50
        assert invoice['payment_term_id'] == 5
        assert invoice['issue_date'] == date(2026, 8, 10)
        assert invoice['due_date'] == date(2026, 9, 9)
        assert invoice['discount_due_date'] == date(2026, 8, 20)
        assert invoice['discount_percentage'] == 2.0
        assert invoice['discount_days'] == 10
        assert invoice['early_discount_amount'] == 40.0  # 2% of 2000.0
        assert invoice['total_amount'] == 2000.0

        # Customer balance updated (100.0 + 2000.0 = 2100.0)
        self.mock_customer_repo.update.assert_called_once_with(105, {'balance': 2100.0}, conn=None)

    def test_create_from_order_inherits_customer_payment_term_when_order_term_omitted(self):
        """When order has no payment_term_id, term is inherited from customer profile."""
        order = {
            'id': 51,
            'order_number': 'SO-00051',
            'customer_id': 106,
            'order_date': date(2026, 8, 12),
            'grand_total': 800.0,
            'payment_term_id': None,
        }
        self.mock_customer_repo.get.return_value = {
            'id': 106,
            'name': 'Beta LLC',
            'payment_term_id': 4,  # Net 60
            'balance': 0.0,
        }
        self.mock_payment_term_repo.get.return_value = {
            'id': 4,
            'name': 'Net 60',
            'code': 'NET_60',
            'due_days': 60,
            'discount_percentage': 0.0,
            'discount_days': 0,
            'is_active': True,
        }
        self.mock_inv_repo.create.side_effect = lambda payload, conn=None: dict(payload, id=501)

        with patch('modules.accounting.services.invoice_service.generate_invoice_number', return_value='INV-00051'):
            invoice = self.service.create_from_order(order)

        assert invoice['payment_term_id'] == 4
        assert invoice['issue_date'] == date(2026, 8, 12)
        assert invoice['due_date'] == date(2026, 10, 11)
        assert invoice['discount_due_date'] is None
        assert invoice['early_discount_amount'] == 0.0

    def test_create_from_order_cod_due_date_equals_order_date(self):
        """COD term results in due_date matching order_date."""
        order = {
            'id': 52,
            'order_number': 'SO-00052',
            'customer_id': 107,
            'order_date': date(2026, 8, 15),
            'grand_total': 350.0,
            'payment_term_id': 2,  # COD
        }
        self.mock_payment_term_repo.get.return_value = {
            'id': 2,
            'name': 'Cash on Delivery (COD)',
            'code': 'COD',
            'due_days': 0,
            'discount_percentage': 0.0,
            'discount_days': 0,
            'is_active': True,
        }
        self.mock_customer_repo.get.return_value = {
            'id': 107,
            'name': 'Cash Retailer',
            'balance': 0.0,
        }
        self.mock_inv_repo.create.side_effect = lambda payload, conn=None: dict(payload, id=502)

        with patch('modules.accounting.services.invoice_service.generate_invoice_number', return_value='INV-00052'):
            invoice = self.service.create_from_order(order)

        assert invoice['due_date'] == date(2026, 8, 15)
        assert invoice['discount_due_date'] is None


class TestInvoiceServiceRecalculateAndInvoiceOrder:
    def setup_method(self):
        self.mock_inv_repo = MagicMock()
        self.mock_customer_repo = MagicMock()
        self.mock_order_repo = MagicMock()
        self.mock_line_repo = MagicMock()
        self.mock_payment_term_repo = MagicMock()

        self.service = InvoiceService(
            repo=self.mock_inv_repo,
            customer_repo=self.mock_customer_repo,
            order_repo=self.mock_order_repo,
            line_repo=self.mock_line_repo,
            payment_term_repo=self.mock_payment_term_repo,
        )

    def test_recalculate_and_invoice_order_end_to_end_with_discounts(self):
        """Order recalculation with catch weight computes discounts on recalculated grand total."""
        self.mock_order_repo.get.return_value = {
            'id': 60,
            'order_number': 'SO-00060',
            'customer_id': 300,
            'subtotal': 1000.0,
            'tax': 100.0,
            'grand_total': 1100.0,
            'freight_amount': 0.0,
            'discount_amount': 0.0,
            'order_date': date(2026, 8, 20),
            'payment_term_id': 5,  # 2/10 Net 30
        }
        self.mock_line_repo.list.return_value = [
            {
                'id': 601,
                'sales_order_id': 60,
                'product_name': 'Parmigiano Reggiano',
                'line_total': 1000.0,
                'is_catch_weight': True,
                'unit_price_pricing_uom': 20.0,
                'nominal_weight': 50.0,
                'catch_weight_actual': 55.0,  # 55kg * $20 = $1100 (+100 subtotal)
                'discount': 0.0,
            }
        ]
        self.mock_customer_repo.get.return_value = {
            'id': 300,
            'name': 'Gourmet Cheese Shop',
            'balance': 200.0,
        }
        self.mock_payment_term_repo.get.return_value = {
            'id': 5,
            'name': '2/10 Net 30',
            'code': '2_10_NET_30',
            'due_days': 30,
            'discount_percentage': 2.0,
            'discount_days': 10,
            'is_active': True,
        }
        self.mock_inv_repo.create.side_effect = lambda payload, conn=None: dict(payload, id=600)

        with patch('modules.accounting.services.invoice_service.generate_invoice_number', return_value='INV-00060'):
            invoice = self.service.recalculate_and_invoice_order(60)

        # Recalculated total: 1100 subtotal + 110 tax (10%) = 1210.0
        assert invoice['total_amount'] == 1210.0
        assert invoice['is_catch_weight'] is True
        assert invoice['nominal_total_weight'] == 50.0
        assert invoice['actual_total_weight'] == 55.0
        assert invoice['weight_adjustment_amount'] == 100.0

        # Due date & Discount metadata computed
        assert invoice['payment_term_id'] == 5
        assert invoice['issue_date'] == date(2026, 8, 20)
        assert invoice['due_date'] == date(2026, 9, 19)
        assert invoice['discount_due_date'] == date(2026, 8, 30)
        assert invoice['discount_percentage'] == 2.0
        assert invoice['discount_days'] == 10
        assert invoice['early_discount_amount'] == 24.20  # 2% of 1210.0

        # Customer balance updated (200.0 + 1210.0 = 1410.0)
        self.mock_customer_repo.update.assert_called_once_with(300, {'balance': 1410.0}, conn=None)