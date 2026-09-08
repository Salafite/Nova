import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from modules.accounting.services.payment_service import (
    PaymentService,
    PAYMENT_REPO,
    INVOICE_REPO,
    CUSTOMER_REPO,
)
from modules.accounting.controllers import T0091I


class InMemoryRepo:
    """In-memory CRUD repository for isolated payment and settlement unit & integration tests."""
    def __init__(self, table_name, items=None):
        self.table_name = table_name
        self.items = {item['id']: dict(item) for item in (items or [])}
        self._next_id = max(self.items.keys(), default=0) + 1

    def get(self, id_val, conn=None, **kwargs):
        item = self.items.get(int(id_val))
        return dict(item) if item else None

    def list(self, filters=None, limit=1000, order_by=None, offset=0, conn=None, **kwargs):
        results = list(self.items.values())
        if filters:
            for k, v in filters.items():
                results = [r for r in results if r.get(k) == v]
        if order_by and isinstance(order_by, str):
            results.sort(key=lambda x: (x.get(order_by) is None, x.get(order_by)))
        return [dict(r) for r in results[offset:offset + limit]]

    def create(self, payload, conn=None, **kwargs):
        new_id = payload.get('id') or self._next_id
        self._next_id = max(self._next_id, new_id + 1)
        record = dict(payload, id=new_id)
        self.items[new_id] = record
        return dict(record)

    def update(self, id_val, payload, conn=None, **kwargs):
        int_id = int(id_val)
        if int_id not in self.items:
            return None
        self.items[int_id].update(payload)
        return dict(self.items[int_id])

    def delete(self, id_val, conn=None, **kwargs):
        return self.items.pop(int(id_val), None) is not None


# ==============================================================================
# 1. Early Payment Discount Evaluation Unit Tests
# ==============================================================================
class TestPaymentServiceEvaluateEarlyDiscount:
    """Unit tests for PaymentService.evaluate_early_discount across various terms and dates."""

    def setup_method(self):
        self.payment_terms = [
            {
                'id': 1,
                'name': 'Net 30',
                'code': 'NET_30',
                'due_days': 30,
                'discount_percentage': 0.0,
                'discount_days': 0,
                'is_active': True,
                'is_default': True,
            },
            {
                'id': 5,
                'name': '2/10 Net 30',
                'code': '2_10_NET_30',
                'due_days': 30,
                'discount_percentage': 2.0,
                'discount_days': 10,
                'is_active': True,
                'is_default': False,
            },
            {
                'id': 6,
                'name': '3/15 Net 45',
                'code': '3_15_NET_45',
                'due_days': 45,
                'discount_percentage': 3.0,
                'discount_days': 15,
                'is_active': True,
                'is_default': False,
            },
        ]

        self.customers = [
            {
                'id': 101,
                'name': 'Early Pay Customer',
                'credit_limit': 50000.0,
                'balance': 1000.0,
                'payment_term_id': 5,  # 2/10 Net 30
            },
            {
                'id': 102,
                'name': 'Standard Net 30 Customer',
                'credit_limit': 20000.0,
                'balance': 2000.0,
                'payment_term_id': 1,  # Net 30
            },
        ]

        self.invoices = [
            {
                'id': 201,
                'invoice_number': 'INV-201',
                'partner_id': 101,
                'payment_term_id': 5,  # 2/10 Net 30
                'issue_date': date(2026, 8, 1),
                'due_date': date(2026, 8, 31),
                'discount_due_date': date(2026, 8, 11),
                'discount_percentage': 2.0,
                'discount_days': 10,
                'early_discount_amount': 20.0,
                'total_amount': 1000.0,
                'discount_amount': 0.0,
                'status': 'Unpaid',
            },
            {
                'id': 202,
                'invoice_number': 'INV-202',
                'partner_id': 102,
                'payment_term_id': 1,  # Net 30 (no discount)
                'issue_date': date(2026, 8, 1),
                'due_date': date(2026, 8, 31),
                'discount_due_date': None,
                'discount_percentage': 0.0,
                'discount_days': 0,
                'early_discount_amount': 0.0,
                'total_amount': 2000.0,
                'discount_amount': 0.0,
                'status': 'Unpaid',
            },
        ]

        self.payment_repo = InMemoryRepo('T0091')
        self.invoice_repo = InMemoryRepo('T0090', self.invoices)
        self.customer_repo = InMemoryRepo('T0010', self.customers)
        self.payment_term_repo = InMemoryRepo('T0096', self.payment_terms)

        self.service = PaymentService(
            repo=self.payment_repo,
            invoice_repo=self.invoice_repo,
            customer_repo=self.customer_repo,
            payment_term_repo=self.payment_term_repo,
        )

    def test_evaluate_early_discount_paid_before_cutoff_is_eligible(self):
        """Payment date before discount cutoff (e.g., Aug 5 for Aug 11 cutoff) is eligible with 2% discount."""
        result = self.service.evaluate_early_discount(
            invoice_id=201,
            payment_date=date(2026, 8, 5),
        )

        assert result['is_eligible'] is True
        assert result['invoice_id'] == 201
        assert result['invoice_total'] == 1000.0
        assert result['balance_due'] == 1000.0
        assert result['discount_percentage'] == 2.0
        assert result['discount_amount'] == 20.0
        assert result['net_amount_due'] == 980.0
        assert result['discount_due_date'] == date(2026, 8, 11)
        assert result['payment_date'] == date(2026, 8, 5)
        assert "Early payment discount of 2% applied" in result['message']

    def test_evaluate_early_discount_paid_on_exact_cutoff_date_is_eligible(self):
        """Payment made on the exact discount cutoff date (Aug 11) is eligible."""
        result = self.service.evaluate_early_discount(
            invoice_id=201,
            payment_date=date(2026, 8, 11),
        )

        assert result['is_eligible'] is True
        assert result['discount_amount'] == 20.0
        assert result['net_amount_due'] == 980.0

    def test_evaluate_early_discount_paid_after_cutoff_is_ineligible(self):
        """Payment date after discount cutoff (Aug 12) is ineligible; discount amount is 0 and full total due."""
        result = self.service.evaluate_early_discount(
            invoice_id=201,
            payment_date=date(2026, 8, 12),
        )

        assert result['is_eligible'] is False
        assert result['discount_amount'] == 0.0
        assert result['net_amount_due'] == 1000.0
        assert "past the early discount cutoff" in result['message']

    def test_evaluate_early_discount_with_grace_period_extends_eligibility(self):
        """Specifying grace_days=2 extends eligibility through Aug 13."""
        # Aug 13 is within 2 days of Aug 11
        within_grace = self.service.evaluate_early_discount(
            invoice_id=201,
            payment_date=date(2026, 8, 13),
            grace_days=2,
        )
        assert within_grace['is_eligible'] is True
        assert within_grace['discount_amount'] == 20.0
        assert within_grace['cutoff_date'] == date(2026, 8, 13)

        # Aug 14 is beyond grace period
        past_grace = self.service.evaluate_early_discount(
            invoice_id=201,
            payment_date=date(2026, 8, 14),
            grace_days=2,
        )
        assert past_grace['is_eligible'] is False
        assert past_grace['discount_amount'] == 0.0
        assert past_grace['net_amount_due'] == 1000.0

    def test_evaluate_early_discount_for_standard_net_30_term_is_ineligible(self):
        """Invoices with standard terms (Net 30) have discount_percentage=0 and are never eligible."""
        result = self.service.evaluate_early_discount(
            invoice_id=202,
            payment_date=date(2026, 8, 5),
        )

        assert result['is_eligible'] is False
        assert result['discount_percentage'] == 0.0
        assert result['discount_amount'] == 0.0
        assert result['net_amount_due'] == 2000.0

    def test_evaluate_early_discount_with_partial_previous_payments(self):
        """When an invoice has already been partially paid, early discount is computed against remaining balance."""
        # Record a prior completed payment of $400 on invoice 201
        self.payment_repo.create({
            'invoice_id': 201,
            'partner_id': 101,
            'amount': 400.0,
            'payment_date': date(2026, 8, 2),
            'status': 'Completed',
        })

        # Remaining balance: 1000 - 400 = 600
        result = self.service.evaluate_early_discount(
            invoice_id=201,
            payment_date=date(2026, 8, 6),
        )

        assert result['is_eligible'] is True
        assert result['invoice_total'] == 1000.0
        assert result['amount_already_paid'] == 400.0
        assert result['balance_due'] == 600.0
        assert result['discount_amount'] == 12.0  # 2% of remaining 600.0
        assert result['net_amount_due'] == 588.0  # 600 - 12 = 588

    def test_evaluate_early_discount_with_custom_payment_amount(self):
        """Evaluating with explicit payment_amount calculates discount for that specified amount."""
        result = self.service.evaluate_early_discount(
            invoice_id=201,
            payment_date=date(2026, 8, 5),
            payment_amount=500.0,
        )

        assert result['is_eligible'] is True
        assert result['discount_amount'] == 10.0  # 2% of 500.0

    def test_evaluate_early_discount_resolves_term_from_customer_when_invoice_missing_term_metadata(self):
        """When invoice lacks discount_due_date and discount_percentage, resolves from customer's term."""
        self.invoice_repo.create({
            'id': 203,
            'invoice_number': 'INV-203',
            'partner_id': 101,  # Has customer term 5 (2/10 Net 30)
            'payment_term_id': None,
            'issue_date': date(2026, 8, 10),
            'due_date': date(2026, 9, 9),
            'discount_due_date': None,
            'discount_percentage': 0.0,
            'discount_days': 0,
            'total_amount': 3000.0,
            'status': 'Unpaid',
        })

        result = self.service.evaluate_early_discount(
            invoice_id=203,
            payment_date=date(2026, 8, 15),
        )

        assert result['is_eligible'] is True
        assert result['discount_percentage'] == 2.0
        assert result['discount_due_date'] == date(2026, 8, 20)  # 2026-08-10 + 10 days
        assert result['discount_amount'] == 60.0  # 2% of 3000.0
        assert result['net_amount_due'] == 2940.0

    def test_evaluate_early_discount_invoice_not_found_raises_value_error(self):
        """Evaluating a non-existent invoice ID raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            self.service.evaluate_early_discount(invoice_id=9999)
        assert "Invoice 9999 not found" in str(exc_info.value)


# ==============================================================================
# 2. Payment Settlement & Discount Honoring Unit & Integration Tests
# ==============================================================================
class TestPaymentServiceSettlementAndDiscounts:
    """Integration tests for PaymentService.create and settle_invoice_payment honoring early discounts."""

    def setup_method(self):
        self.payment_terms = [
            {
                'id': 5,
                'name': '2/10 Net 30',
                'code': '2_10_NET_30',
                'due_days': 30,
                'discount_percentage': 2.0,
                'discount_days': 10,
                'is_active': True,
            },
            {
                'id': 6,
                'name': '3/15 Net 45',
                'code': '3_15_NET_45',
                'due_days': 45,
                'discount_percentage': 3.0,
                'discount_days': 15,
                'is_active': True,
            },
        ]

        self.customers = [
            {
                'id': 101,
                'name': 'Early Pay Partner',
                'credit_limit': 50000.0,
                'balance': 1000.0,
                'payment_term_id': 5,
            },
            {
                'id': 102,
                'name': 'Tier Partner',
                'credit_limit': 50000.0,
                'balance': 5000.0,
                'payment_term_id': 6,
            },
        ]

        self.invoices = [
            {
                'id': 301,
                'invoice_number': 'INV-301',
                'partner_id': 101,
                'payment_term_id': 5,  # 2/10 Net 30
                'issue_date': date(2026, 8, 1),
                'due_date': date(2026, 8, 31),
                'discount_due_date': date(2026, 8, 11),
                'discount_percentage': 2.0,
                'discount_days': 10,
                'early_discount_amount': 20.0,
                'total_amount': 1000.0,
                'discount_amount': 0.0,
                'status': 'Unpaid',
            },
            {
                'id': 302,
                'invoice_number': 'INV-302',
                'partner_id': 102,
                'payment_term_id': 6,  # 3/15 Net 45
                'issue_date': date(2026, 8, 1),
                'due_date': date(2026, 9, 15),
                'discount_due_date': date(2026, 8, 16),
                'discount_percentage': 3.0,
                'discount_days': 15,
                'early_discount_amount': 150.0,
                'total_amount': 5000.0,
                'discount_amount': 0.0,
                'status': 'Unpaid',
            },
        ]

        self.payment_repo = InMemoryRepo('T0091')
        self.invoice_repo = InMemoryRepo('T0090', self.invoices)
        self.customer_repo = InMemoryRepo('T0010', self.customers)
        self.payment_term_repo = InMemoryRepo('T0096', self.payment_terms)

        self.service = PaymentService(
            repo=self.payment_repo,
            invoice_repo=self.invoice_repo,
            customer_repo=self.customer_repo,
            payment_term_repo=self.payment_term_repo,
        )

    def test_full_payment_before_cutoff_honors_discount_and_settles_invoice(self):
        """Paying net amount ($980) before cutoff settles $1000 invoice, updates discount_amount to $20, marks Paid."""
        payment_payload = {
            'invoice_id': 301,
            'partner_id': 101,
            'amount': 980.0,
            'payment_date': date(2026, 8, 5),
            'payment_method': 'Bank Transfer',
            'status': 'Completed',
        }

        payment = self.service.create(payment_payload)

        assert payment['id'] is not None
        assert payment['amount'] == 980.0
        assert "Early payment discount applied: $20.00 (2%)" in payment['notes']

        # Verify invoice is updated: discount_amount is $20.0, status is Paid
        updated_inv = self.invoice_repo.get(301)
        assert updated_inv['discount_amount'] == 20.0
        assert updated_inv['status'] == 'Paid'

        # Verify customer balance reduced by full settlement credit ($1000: $980 cash + $20 discount)
        updated_cust = self.customer_repo.get(101)
        assert updated_cust['balance'] == 0.0

    def test_full_gross_payment_before_cutoff_applies_discount_and_settles_invoice(self):
        """Paying full gross amount ($1000) before cutoff settles invoice and gives full credit."""
        payment_payload = {
            'invoice_id': 301,
            'partner_id': 101,
            'amount': 1000.0,
            'payment_date': date(2026, 8, 8),
            'payment_method': 'Credit Card',
            'status': 'Completed',
        }

        payment = self.service.create(payment_payload)

        updated_inv = self.invoice_repo.get(301)
        assert updated_inv['discount_amount'] == 20.0
        assert updated_inv['status'] == 'Paid'

        updated_cust = self.customer_repo.get(101)
        assert updated_cust['balance'] == 0.0

    def test_payment_after_cutoff_does_not_apply_early_discount(self):
        """Paying after discount deadline (Aug 12 for Aug 11 cutoff) earns 0 discount."""
        payment_payload = {
            'invoice_id': 301,
            'partner_id': 101,
            'amount': 980.0,
            'payment_date': date(2026, 8, 12),
            'payment_method': 'Check',
            'status': 'Completed',
        }

        payment = self.service.create(payment_payload)

        assert "Early payment discount applied" not in (payment.get('notes') or '')

        # Invoice discount is unchanged (0.0), status is Partially Paid because $980 < $1000
        updated_inv = self.invoice_repo.get(301)
        assert updated_inv['discount_amount'] == 0.0
        assert updated_inv['status'] == 'Partially Paid'

        # Customer balance reduced only by cash amount ($980), leaving $20 balance
        updated_cust = self.customer_repo.get(101)
        assert updated_cust['balance'] == 20.0

    def test_full_payment_after_cutoff_settles_invoice_without_discount(self):
        """Paying full $1000 after cutoff settles invoice as Paid with discount_amount=0."""
        payment_payload = {
            'invoice_id': 301,
            'partner_id': 101,
            'amount': 1000.0,
            'payment_date': date(2026, 8, 15),
            'payment_method': 'Bank Transfer',
            'status': 'Completed',
        }

        self.service.create(payment_payload)

        updated_inv = self.invoice_repo.get(301)
        assert updated_inv['discount_amount'] == 0.0
        assert updated_inv['status'] == 'Paid'

        updated_cust = self.customer_repo.get(101)
        assert updated_cust['balance'] == 0.0

    def test_apply_early_discount_false_flag_disables_discount_application(self):
        """Setting apply_early_discount=False ignores discount even when payment is made before cutoff."""
        payment_payload = {
            'invoice_id': 301,
            'partner_id': 101,
            'amount': 980.0,
            'payment_date': date(2026, 8, 5),
            'payment_method': 'Bank Transfer',
            'status': 'Completed',
        }

        payment = self.service.create(payment_payload, apply_early_discount=False)

        assert "Early payment discount applied" not in (payment.get('notes') or '')
        updated_inv = self.invoice_repo.get(301)
        assert updated_inv['discount_amount'] == 0.0
        assert updated_inv['status'] == 'Partially Paid'

    def test_proportional_discount_for_partial_payment_before_cutoff(self):
        """Partial payment before cutoff earns proportional discount credit."""
        # Invoice 302: Total $5000 with 3% discount (Net due is $4850, discount $150).
        # Customer pays half ($2425 cash).
        # Proportional discount: $2425 * (3 / 97) = $75.0 discount credit.
        # Total credit: $2425 + $75 = $2500 (half of gross $5000).
        payment_payload = {
            'invoice_id': 302,
            'partner_id': 102,
            'amount': 2425.0,
            'payment_date': date(2026, 8, 10),
            'payment_method': 'Wire Transfer',
            'status': 'Completed',
        }

        payment = self.service.create(payment_payload)

        assert "Early payment discount applied: $75.00 (3%)" in payment['notes']

        # Invoice updated with $75 discount, status Partially Paid
        updated_inv = self.invoice_repo.get(302)
        assert updated_inv['discount_amount'] == 75.0
        assert updated_inv['status'] == 'Partially Paid'

        # Customer balance reduced by $2500 ($5000 - $2500 = $2500)
        updated_cust = self.customer_repo.get(102)
        assert updated_cust['balance'] == 2500.0

    def test_sequential_payments_settle_invoice_with_multiple_early_discounts(self):
        """Two partial payments made within discount window both earn early discounts and fully settle invoice."""
        # Payment 1: $2425 on Aug 5 (earns $75 discount, credit $2500)
        p1 = self.service.create({
            'invoice_id': 302,
            'partner_id': 102,
            'amount': 2425.0,
            'payment_date': date(2026, 8, 5),
            'status': 'Completed',
        })
        assert "Early payment discount applied: $75.00" in p1['notes']

        # Payment 2: Remaining $2425 on Aug 12 (before Aug 16 cutoff, earns another $75 discount)
        p2 = self.service.create({
            'invoice_id': 302,
            'partner_id': 102,
            'amount': 2425.0,
            'payment_date': date(2026, 8, 12),
            'status': 'Completed',
        })
        assert "Early payment discount applied: $75.00" in p2['notes']

        # Total paid: $4850 cash + $150 discounts = $5000 total -> Invoice is Paid!
        updated_inv = self.invoice_repo.get(302)
        assert updated_inv['discount_amount'] == 150.0
        assert updated_inv['status'] == 'Paid'

        # Customer balance is 0.0
        updated_cust = self.customer_repo.get(102)
        assert updated_cust['balance'] == 0.0

    def test_settle_invoice_payment_convenience_method(self):
        """settle_invoice_payment returns payment, updated invoice, and customer records in a single payload."""
        result = self.service.settle_invoice_payment({
            'invoice_id': 301,
            'partner_id': 101,
            'amount': 980.0,
            'payment_date': date(2026, 8, 5),
            'status': 'Completed',
        })

        assert 'payment' in result
        assert 'invoice' in result
        assert 'customer' in result

        assert result['payment']['amount'] == 980.0
        assert result['invoice']['status'] == 'Paid'
        assert result['invoice']['discount_amount'] == 20.0
        assert result['customer']['balance'] == 0.0

    def test_unlinked_payment_updates_customer_balance_without_invoice(self):
        """Payment without invoice_id applies cash credit directly to customer balance."""
        payment = self.service.create({
            'partner_id': 101,
            'amount': 300.0,
            'payment_date': date(2026, 8, 5),
            'status': 'Completed',
        })

        assert payment['id'] is not None
        updated_cust = self.customer_repo.get(101)
        assert updated_cust['balance'] == 700.0  # 1000.0 - 300.0 = 700.0

    def test_payment_with_zero_or_negative_amount_raises_value_error(self):
        """Creating a payment with amount <= 0 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            self.service.create({'invoice_id': 301, 'amount': 0.0})
        assert "Payment amount must be greater than 0" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            self.service.create({'invoice_id': 301, 'amount': -50.0})
        assert "Payment amount must be greater than 0" in str(exc_info.value)

    def test_payment_for_missing_invoice_raises_value_error(self):
        """Payment referencing non-existent invoice_id raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            self.service.create({'invoice_id': 99999, 'amount': 100.0})
        assert "Invoice 99999 not found" in str(exc_info.value)


# ==============================================================================
# 3. Payments Controller (T0091I) Endpoint Tests
# ==============================================================================
class TestPaymentControllerDiscountPreviewEndpoints:
    """Tests for T0091I discount preview routes."""

    def test_preview_invoice_payment_discount_endpoint_success(self, monkeypatch):
        """GET /api/T0091I/invoice/{id}/discount-preview returns structured preview."""
        mock_svc = MagicMock()
        mock_svc.preview_payment_discount.return_value = {
            'invoice_id': 100,
            'invoice_number': 'INV-100',
            'partner_id': 50,
            'invoice_total': 1000.0,
            'amount_already_paid': 0.0,
            'balance_due': 1000.0,
            'is_eligible': True,
            'discount_percentage': 2.0,
            'discount_amount': 20.0,
            'net_amount_due': 980.0,
            'discount_due_date': date(2026, 8, 15),
            'payment_date': date(2026, 8, 10),
            'message': 'Early payment discount of 2% applied',
        }
        monkeypatch.setattr(T0091I, 'service', mock_svc)

        result = T0091I.preview_invoice_payment_discount(
            invoice_id=100,
            payment_date="2026-08-10",
            payment_amount=1000.0,
            grace_days=0,
        )

        assert result['invoice_id'] == 100
        assert result['is_eligible'] is True
        assert result['discount_amount'] == 20.0
        assert result['net_amount_due'] == 980.0
        mock_svc.preview_payment_discount.assert_called_once_with(
            invoice_id=100,
            payment_date="2026-08-10",
            payment_amount=1000.0,
            grace_days=0,
        )

    def test_preview_invoice_payment_discount_endpoint_404_when_invoice_not_found(self, monkeypatch):
        """GET /api/T0091I/invoice/{id}/discount-preview raises 404 when invoice does not exist."""
        mock_svc = MagicMock()
        mock_svc.preview_payment_discount.side_effect = ValueError("Invoice 999 not found")
        monkeypatch.setattr(T0091I, 'service', mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            T0091I.preview_invoice_payment_discount(invoice_id=999)
        assert exc_info.value.status_code == 404
        assert "Invoice 999 not found" in exc_info.value.detail

    def test_preview_invoice_payment_discount_endpoint_400_on_invalid_parameters(self, monkeypatch):
        """GET /api/T0091I/invoice/{id}/discount-preview raises 400 when invalid input is provided."""
        mock_svc = MagicMock()
        mock_svc.preview_payment_discount.side_effect = ValueError("Invalid payment parameter")
        monkeypatch.setattr(T0091I, 'service', mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            T0091I.preview_invoice_payment_discount(invoice_id=100)
        assert exc_info.value.status_code == 400
        assert "Invalid payment parameter" in exc_info.value.detail
