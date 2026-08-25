import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from modules.sales.services.sales_service import SalesOrderService
from modules.sales.services.enhanced_sales_order_service import EnhancedSalesOrderService
from modules.sales.controllers import T0012I


class InMemoryRepo:
    """In-memory CRUD repository for sales order delivery and payment terms integration tests."""
    def __init__(self, table_name, items=None):
        self.table_name = table_name
        self.items = {item['id']: dict(item) for item in (items or [])}
        self._next_id = max(self.items.keys(), default=0) + 1

    def get(self, id_val, conn=None, **kwargs):
        item = self.items.get(id_val)
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
        if id_val not in self.items:
            return None
        self.items[id_val].update(payload)
        return dict(self.items[id_val])

    def delete(self, id_val, conn=None, **kwargs):
        return self.items.pop(id_val, None) is not None


class TestSalesOrderPaymentTermInheritance:
    """Tests for Sales Order payment term resolution and inheritance upon order creation."""

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
                'id': 2,
                'name': 'Net 15',
                'code': 'NET_15',
                'due_days': 15,
                'discount_percentage': 0.0,
                'discount_days': 0,
                'is_active': True,
                'is_default': False,
            },
            {
                'id': 3,
                'name': '2/10 Net 30',
                'code': '2_10_NET_30',
                'due_days': 30,
                'discount_percentage': 2.0,
                'discount_days': 10,
                'is_active': True,
                'is_default': False,
            },
            {
                'id': 4,
                'name': 'Net 60',
                'code': 'NET_60',
                'due_days': 60,
                'discount_percentage': 0.0,
                'discount_days': 0,
                'is_active': True,
                'is_default': False,
            },
        ]

        self.customers = [
            {
                'id': 101,
                'name': 'Acme Corp (Net 15)',
                'credit_limit': 10000.0,
                'balance': 500.0,
                'payment_term_id': 2,  # Net 15
            },
            {
                'id': 102,
                'name': 'Global Trading (2/10 Net 30)',
                'credit_limit': 20000.0,
                'balance': 0.0,
                'payment_term_id': 3,  # 2/10 Net 30
            },
            {
                'id': 103,
                'name': 'No Term Assigned Client',
                'credit_limit': 5000.0,
                'balance': 0.0,
                'payment_term_id': None,
            },
        ]

        self.order_repo = InMemoryRepo('T0012')
        self.line_repo = InMemoryRepo('T0013')
        self.customer_repo = InMemoryRepo('T0010', self.customers)
        self.inv_repo = InMemoryRepo('T0090')
        self.pl_repo = InMemoryRepo('T0101')
        self.pli_repo = InMemoryRepo('T0102')
        self.product_repo = InMemoryRepo('T0003')
        self.payment_term_repo = InMemoryRepo('T0096', self.payment_terms)

        self.service = SalesOrderService(
            repo=self.order_repo,
            line_repo=self.line_repo,
            customer_repo=self.customer_repo,
            inv_repo=self.inv_repo,
            pl_repo=self.pl_repo,
            pli_repo=self.pli_repo,
            product_repo=self.product_repo,
            payment_term_repo=self.payment_term_repo,
        )

    def test_order_creation_inherits_customer_payment_term(self):
        """Creating an order without explicit payment_term_id inherits customer payment_term_id (Net 15)."""
        order = self.service.create({
            'order_number': 'SO-001',
            'customer_id': 101,
            'subtotal': 1000.0,
            'tax': 50.0,
            'grand_total': 1050.0,
            'order_date': date(2026, 8, 1),
            'status': 'Pending',
        })

        assert order['id'] is not None
        assert order['customer_id'] == 101
        assert order['payment_term_id'] == 2  # Inherited from Acme Corp (Net 15)

    def test_order_creation_explicit_payment_term_overrides_customer_term(self):
        """Providing an explicit payment_term_id overrides the customer's assigned term."""
        order = self.service.create({
            'order_number': 'SO-002',
            'customer_id': 101,  # Has Net 15
            'payment_term_id': 4,  # Overridden with Net 60
            'subtotal': 1000.0,
            'tax': 0.0,
            'grand_total': 1000.0,
            'order_date': date(2026, 8, 1),
            'status': 'Pending',
        })

        assert order['payment_term_id'] == 4  # Net 60

    def test_order_creation_falls_back_to_default_active_term_when_customer_has_no_term(self):
        """When customer has no payment term assigned, falls back to active default term (Net 30)."""
        order = self.service.create({
            'order_number': 'SO-003',
            'customer_id': 103,  # payment_term_id is None
            'subtotal': 500.0,
            'tax': 0.0,
            'grand_total': 500.0,
            'order_date': date(2026, 8, 1),
            'status': 'Pending',
        })

        assert order['payment_term_id'] == 1  # Net 30 default

    def test_order_creation_without_customer_or_default_term_leaves_term_none(self):
        """When no default term exists and no customer term exists, payment_term_id is None."""
        empty_terms_repo = InMemoryRepo('T0096', [])
        service = SalesOrderService(
            repo=self.order_repo,
            line_repo=self.line_repo,
            customer_repo=self.customer_repo,
            inv_repo=self.inv_repo,
            payment_term_repo=empty_terms_repo,
        )

        order = service.create({
            'order_number': 'SO-004',
            'customer_id': 103,
            'subtotal': 200.0,
            'tax': 0.0,
            'grand_total': 200.0,
            'order_date': date(2026, 8, 1),
            'status': 'Pending',
        })

        assert order.get('payment_term_id') is None

    def test_enhanced_service_create_with_lines_inherits_customer_payment_term(self):
        """EnhancedSalesOrderService.create_with_lines inherits customer payment terms."""
        enhanced_svc = EnhancedSalesOrderService(self.order_repo)
        enhanced_svc.customer_repo = self.customer_repo
        enhanced_svc.payment_term_repo = self.payment_term_repo
        enhanced_svc.line_repo = self.line_repo

        order_data = {
            'order_number': 'SO-005',
            'customer_id': 102,  # 2/10 Net 30
            'order_date': date(2026, 8, 1),
            'status': 'Pending',
        }
        lines = [
            {'product_id': 1, 'product_name': 'Item A', 'qty': 2, 'unit_price': 100.0}
        ]

        result = enhanced_svc.create_with_lines(order_data, lines)
        assert result['payment_term_id'] == 3  # 2/10 Net 30


class TestSalesOrderDeliveryInvoicingDueDates:
    """Integration tests verifying invoice creation and dynamic due date calculation upon order delivery."""

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
                'id': 2,
                'name': 'Net 15',
                'code': 'NET_15',
                'due_days': 15,
                'discount_percentage': 0.0,
                'discount_days': 0,
                'is_active': True,
                'is_default': False,
            },
            {
                'id': 3,
                'name': 'Net 60',
                'code': 'NET_60',
                'due_days': 60,
                'discount_percentage': 0.0,
                'discount_days': 0,
                'is_active': True,
                'is_default': False,
            },
            {
                'id': 4,
                'name': 'Cash on Delivery (COD)',
                'code': 'COD',
                'due_days': 0,
                'discount_percentage': 0.0,
                'discount_days': 0,
                'is_active': True,
                'is_default': False,
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
                'id': 201,
                'name': 'Retailer One',
                'credit_limit': 50000.0,
                'balance': 1000.0,
                'payment_term_id': 1,  # Net 30
            },
            {
                'id': 202,
                'name': 'Quick Pay Retailer',
                'credit_limit': 50000.0,
                'balance': 2000.0,
                'payment_term_id': 2,  # Net 15
            },
            {
                'id': 203,
                'name': 'Long Term Client',
                'credit_limit': 50000.0,
                'balance': 0.0,
                'payment_term_id': 3,  # Net 60
            },
            {
                'id': 204,
                'name': 'Cash Customer',
                'credit_limit': 10000.0,
                'balance': 0.0,
                'payment_term_id': 4,  # COD
            },
        ]

        self.order_repo = InMemoryRepo('T0012')
        self.line_repo = InMemoryRepo('T0013')
        self.customer_repo = InMemoryRepo('T0010', self.customers)
        self.inv_repo = InMemoryRepo('T0090')
        self.pl_repo = InMemoryRepo('T0101')
        self.pli_repo = InMemoryRepo('T0102')
        self.product_repo = InMemoryRepo('T0003')
        self.payment_term_repo = InMemoryRepo('T0096', self.payment_terms)

        self.service = SalesOrderService(
            repo=self.order_repo,
            line_repo=self.line_repo,
            customer_repo=self.customer_repo,
            inv_repo=self.inv_repo,
            pl_repo=self.pl_repo,
            pli_repo=self.pli_repo,
            product_repo=self.product_repo,
            payment_term_repo=self.payment_term_repo,
        )

    def test_delivery_generates_invoice_with_net_30_due_date(self):
        """Delivering an order with Net 30 computes due_date as issue_date + 30 days."""
        order = self.order_repo.create({
            'id': 10,
            'order_number': 'SO-010',
            'customer_id': 201,
            'status': 'Shipped',
            'order_date': date(2026, 8, 10),
            'subtotal': 1000.0,
            'tax': 100.0,
            'grand_total': 1100.0,
            'payment_term_id': 1,  # Net 30
        })

        with patch.object(self.service, '_generate_invoice_number', return_value='INV-00010'):
            self.service.update(10, {'status': 'Delivered'})

        invoices = self.inv_repo.list(filters={'sales_order_id': 10})
        assert len(invoices) == 1
        inv = invoices[0]

        assert inv['invoice_number'] == 'INV-00010'
        assert inv['partner_id'] == 201
        assert inv['sales_order_id'] == 10
        assert inv['payment_term_id'] == 1
        assert inv['issue_date'] == date(2026, 8, 10)
        assert inv['due_date'] == date(2026, 9, 9)  # 2026-08-10 + 30 days (Aug has 31 days)
        assert inv['discount_due_date'] is None
        assert inv['discount_percentage'] == 0.0
        assert inv['discount_days'] == 0
        assert inv['early_discount_amount'] == 0.0
        assert inv['total_amount'] == 1100.0
        assert inv['status'] == 'Unpaid'

        # Customer balance updated (1000.0 + 1100.0 = 2100.0)
        updated_cust = self.customer_repo.get(201)
        assert updated_cust['balance'] == 2100.0

    def test_delivery_generates_invoice_with_net_15_due_date(self):
        """Delivering an order with Net 15 computes due_date as issue_date + 15 days."""
        order = self.order_repo.create({
            'id': 11,
            'order_number': 'SO-011',
            'customer_id': 202,
            'status': 'Shipped',
            'order_date': date(2026, 8, 15),
            'subtotal': 500.0,
            'tax': 0.0,
            'grand_total': 500.0,
            'payment_term_id': 2,  # Net 15
        })

        with patch.object(self.service, '_generate_invoice_number', return_value='INV-00011'):
            self.service.update(11, {'status': 'Delivered'})

        invoices = self.inv_repo.list(filters={'sales_order_id': 11})
        assert len(invoices) == 1
        inv = invoices[0]

        assert inv['payment_term_id'] == 2
        assert inv['issue_date'] == date(2026, 8, 15)
        assert inv['due_date'] == date(2026, 8, 30)  # 2026-08-15 + 15 days
        assert inv['discount_due_date'] is None

    def test_delivery_generates_invoice_with_net_60_due_date(self):
        """Delivering an order with Net 60 computes due_date as issue_date + 60 days."""
        order = self.order_repo.create({
            'id': 12,
            'order_number': 'SO-012',
            'customer_id': 203,
            'status': 'Shipped',
            'order_date': date(2026, 8, 1),
            'subtotal': 3000.0,
            'tax': 300.0,
            'grand_total': 3300.0,
            'payment_term_id': 3,  # Net 60
        })

        with patch.object(self.service, '_generate_invoice_number', return_value='INV-00012'):
            self.service.update(12, {'status': 'Delivered'})

        invoices = self.inv_repo.list(filters={'sales_order_id': 12})
        assert len(invoices) == 1
        inv = invoices[0]

        assert inv['payment_term_id'] == 3
        assert inv['issue_date'] == date(2026, 8, 1)
        assert inv['due_date'] == date(2026, 9, 30)  # Aug (31) + Sep (29) = 60 days
        assert inv['discount_due_date'] is None

    def test_delivery_generates_invoice_with_cod_due_date(self):
        """Delivering an order with COD (due_days=0) sets due_date equal to issue_date."""
        order = self.order_repo.create({
            'id': 13,
            'order_number': 'SO-013',
            'customer_id': 204,
            'status': 'Shipped',
            'order_date': date(2026, 8, 20),
            'subtotal': 450.0,
            'tax': 0.0,
            'grand_total': 450.0,
            'payment_term_id': 4,  # COD
        })

        with patch.object(self.service, '_generate_invoice_number', return_value='INV-00013'):
            self.service.update(13, {'status': 'Delivered'})

        invoices = self.inv_repo.list(filters={'sales_order_id': 13})
        assert len(invoices) == 1
        inv = invoices[0]

        assert inv['payment_term_id'] == 4
        assert inv['issue_date'] == date(2026, 8, 20)
        assert inv['due_date'] == date(2026, 8, 20)  # COD same day
        assert inv['discount_due_date'] is None

    def test_delivery_inherits_customer_payment_term_when_order_lacks_payment_term_id(self):
        """When an order has payment_term_id=None, delivery resolves term from customer profile."""
        order = self.order_repo.create({
            'id': 14,
            'order_number': 'SO-014',
            'customer_id': 202,  # Quick Pay Retailer (Net 15)
            'status': 'Shipped',
            'order_date': date(2026, 8, 5),
            'subtotal': 800.0,
            'tax': 0.0,
            'grand_total': 800.0,
            'payment_term_id': None,
        })

        with patch.object(self.service, '_generate_invoice_number', return_value='INV-00014'):
            self.service.update(14, {'status': 'Delivered'})

        invoices = self.inv_repo.list(filters={'sales_order_id': 14})
        assert len(invoices) == 1
        inv = invoices[0]

        assert inv['payment_term_id'] == 2  # Inherited customer Net 15
        assert inv['due_date'] == date(2026, 8, 20)  # 2026-08-05 + 15 days

    def test_delivery_resolves_system_default_when_neither_order_nor_customer_has_term(self):
        """When neither order nor customer has a term, delivery falls back to default active term (Net 30)."""
        cust = self.customer_repo.create({
            'id': 205,
            'name': 'Unknown Terms Client',
            'credit_limit': 10000.0,
            'balance': 0.0,
            'payment_term_id': None,
        })

        order = self.order_repo.create({
            'id': 15,
            'order_number': 'SO-015',
            'customer_id': 205,
            'status': 'Shipped',
            'order_date': date(2026, 8, 1),
            'subtotal': 1500.0,
            'tax': 0.0,
            'grand_total': 1500.0,
            'payment_term_id': None,
        })

        with patch.object(self.service, '_generate_invoice_number', return_value='INV-00015'):
            self.service.update(15, {'status': 'Delivered'})

        invoices = self.inv_repo.list(filters={'sales_order_id': 15})
        assert len(invoices) == 1
        inv = invoices[0]

        assert inv['payment_term_id'] == 1  # Default Net 30
        assert inv['due_date'] == date(2026, 8, 31)  # 2026-08-01 + 30 days


class TestSalesOrderDeliveryEarlyPaymentDiscount:
    """Integration tests verifying discount due date and early discount amount calculations upon delivery."""

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
                'id': 301,
                'name': 'Early Discount Partner',
                'credit_limit': 100000.0,
                'balance': 0.0,
                'payment_term_id': 5,  # 2/10 Net 30
            },
        ]

        self.order_repo = InMemoryRepo('T0012')
        self.line_repo = InMemoryRepo('T0013')
        self.customer_repo = InMemoryRepo('T0010', self.customers)
        self.inv_repo = InMemoryRepo('T0090')
        self.pl_repo = InMemoryRepo('T0101')
        self.pli_repo = InMemoryRepo('T0102')
        self.product_repo = InMemoryRepo('T0003')
        self.payment_term_repo = InMemoryRepo('T0096', self.payment_terms)

        self.service = SalesOrderService(
            repo=self.order_repo,
            line_repo=self.line_repo,
            customer_repo=self.customer_repo,
            inv_repo=self.inv_repo,
            pl_repo=self.pl_repo,
            pli_repo=self.pli_repo,
            product_repo=self.product_repo,
            payment_term_repo=self.payment_term_repo,
        )

    def test_delivery_generates_invoice_with_2_10_net_30_discount_deadline_and_amount(self):
        """Order delivered with 2/10 Net 30 calculates discount_due_date and early_discount_amount."""
        order = self.order_repo.create({
            'id': 20,
            'order_number': 'SO-020',
            'customer_id': 301,
            'status': 'Shipped',
            'order_date': date(2026, 8, 1),
            'subtotal': 1000.0,
            'tax': 0.0,
            'grand_total': 1000.0,
            'payment_term_id': 5,  # 2/10 Net 30
        })

        with patch.object(self.service, '_generate_invoice_number', return_value='INV-00020'):
            self.service.update(20, {'status': 'Delivered'})

        inv = self.inv_repo.list(filters={'sales_order_id': 20})[0]

        assert inv['issue_date'] == date(2026, 8, 1)
        assert inv['due_date'] == date(2026, 8, 31)  # 30 days
        assert inv['discount_due_date'] == date(2026, 8, 11)  # 10 days
        assert inv['discount_percentage'] == 2.0
        assert inv['discount_days'] == 10
        assert inv['early_discount_amount'] == 20.0  # 2% of 1000.0

    def test_delivery_generates_invoice_with_3_15_net_45_discount_deadline_and_amount(self):
        """Order delivered with 3/15 Net 45 calculates discount_due_date and 3% early discount amount."""
        order = self.order_repo.create({
            'id': 21,
            'order_number': 'SO-021',
            'customer_id': 301,
            'status': 'Shipped',
            'order_date': date(2026, 7, 10),
            'subtotal': 2500.0,
            'tax': 0.0,
            'grand_total': 2500.0,
            'payment_term_id': 6,  # 3/15 Net 45
        })

        with patch.object(self.service, '_generate_invoice_number', return_value='INV-00021'):
            self.service.update(21, {'status': 'Delivered'})

        inv = self.inv_repo.list(filters={'sales_order_id': 21})[0]

        assert inv['issue_date'] == date(2026, 7, 10)
        assert inv['due_date'] == date(2026, 8, 24)  # 45 days
        assert inv['discount_due_date'] == date(2026, 7, 25)  # 15 days
        assert inv['discount_percentage'] == 3.0
        assert inv['discount_days'] == 15
        assert inv['early_discount_amount'] == 75.0  # 3% of 2500.0


class TestSalesOrderDeliveryCatchWeightInvoicingWithPaymentTerms:
    """Integration tests verifying catch-weight recalculation combined with payment terms on delivery."""

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
        ]

        self.customers = [
            {
                'id': 401,
                'name': 'Artisan Fromagerie',
                'credit_limit': 50000.0,
                'balance': 0.0,
                'payment_term_id': 5,
            },
        ]

        self.products = [
            {
                'id': 101,
                'name': 'Parmigiano Wheel',
                'is_catch_weight': True,
                'pricing_uom_id': 2,
                'nominal_weight': 40.0,
                'price': 600.0,
            }
        ]

        self.order_repo = InMemoryRepo('T0012')
        self.line_repo = InMemoryRepo('T0013')
        self.customer_repo = InMemoryRepo('T0010', self.customers)
        self.inv_repo = InMemoryRepo('T0090')
        self.pl_repo = InMemoryRepo('T0101')
        self.pli_repo = InMemoryRepo('T0102')
        self.product_repo = InMemoryRepo('T0003', self.products)
        self.payment_term_repo = InMemoryRepo('T0096', self.payment_terms)

        self.service = SalesOrderService(
            repo=self.order_repo,
            line_repo=self.line_repo,
            customer_repo=self.customer_repo,
            inv_repo=self.inv_repo,
            pl_repo=self.pl_repo,
            pli_repo=self.pli_repo,
            product_repo=self.product_repo,
            payment_term_repo=self.payment_term_repo,
        )

    def test_delivery_recalculates_catch_weight_and_applies_terms_on_adjusted_total(self):
        """Catch-weight order delivery recalculates scale weight total and applies early discount on new total."""
        order = self.order_repo.create({
            'id': 30,
            'order_number': 'SO-030',
            'customer_id': 401,
            'status': 'Shipped',
            'order_date': date(2026, 8, 10),
            'subtotal': 600.0,
            'tax': 0.0,
            'grand_total': 600.0,
            'payment_term_id': 5,  # 2/10 Net 30
        })

        line = self.line_repo.create({
            'id': 301,
            'sales_order_id': 30,
            'product_id': 101,
            'product_name': 'Parmigiano Wheel',
            'qty': 1.0,
            'unit_price': 600.0,
            'line_total': 600.0,
            'is_catch_weight': True,
            'pricing_uom_id': 2,
            'unit_price_pricing_uom': 15.0,  # $15/kg
            'nominal_weight': 40.0,
            'catch_weight_actual': 44.0,  # 44kg * $15 = $660 (+60 adjustment)
        })

        with patch.object(self.service, '_generate_invoice_number', return_value='INV-00030'):
            self.service.update(30, {'status': 'Delivered'})

        # Verify order totals recalculated
        updated_order = self.order_repo.get(30)
        assert updated_order['subtotal'] == 660.0
        assert updated_order['grand_total'] == 660.0
        assert updated_order['status'] == 'Delivered'

        # Verify invoice
        inv = self.inv_repo.list(filters={'sales_order_id': 30})[0]
        assert inv['total_amount'] == 660.0
        assert inv['is_catch_weight'] is True
        assert inv['actual_total_weight'] == 44.0
        assert inv['nominal_total_weight'] == 40.0
        assert inv['weight_adjustment_amount'] == 60.0

        # Verify payment terms & discount computed on recalculated $660 total
        assert inv['payment_term_id'] == 5
        assert inv['issue_date'] == date(2026, 8, 10)
        assert inv['due_date'] == date(2026, 9, 9)
        assert inv['discount_due_date'] == date(2026, 8, 20)
        assert inv['early_discount_amount'] == 13.20  # 2% of 660.0

        # Customer balance updated with recalculated total
        assert self.customer_repo.get(401)['balance'] == 660.0


class TestSalesOrderStatusTransitionsAndValidation:
    """Tests for status transitions and delivery gating."""

    def setup_method(self):
        self.order_repo = InMemoryRepo('T0012')
        self.line_repo = InMemoryRepo('T0013')
        self.customer_repo = InMemoryRepo('T0010')
        self.inv_repo = InMemoryRepo('T0090')
        self.pl_repo = InMemoryRepo('T0101')
        self.pli_repo = InMemoryRepo('T0102')
        self.product_repo = InMemoryRepo('T0003')
        self.payment_term_repo = InMemoryRepo('T0096')

        self.service = SalesOrderService(
            repo=self.order_repo,
            line_repo=self.line_repo,
            customer_repo=self.customer_repo,
            inv_repo=self.inv_repo,
            pl_repo=self.pl_repo,
            pli_repo=self.pli_repo,
            product_repo=self.product_repo,
            payment_term_repo=self.payment_term_repo,
        )

    def test_invalid_status_transition_from_draft_to_delivered_raises_400(self):
        """Transitioning directly from Draft to Delivered is not allowed."""
        order = self.order_repo.create({
            'id': 40,
            'order_number': 'SO-040',
            'customer_id': 1,
            'status': 'Draft',
            'grand_total': 100.0,
        })

        with pytest.raises(HTTPException) as exc_info:
            self.service.update(40, {'status': 'Delivered'})
        assert exc_info.value.status_code == 400
        assert "Invalid status transition" in exc_info.value.detail

    def test_invalid_status_transition_from_pending_to_delivered_raises_400(self):
        """Transitioning directly from Pending to Delivered is not allowed."""
        order = self.order_repo.create({
            'id': 41,
            'order_number': 'SO-041',
            'customer_id': 1,
            'status': 'Pending',
            'grand_total': 100.0,
        })

        with pytest.raises(HTTPException) as exc_info:
            self.service.update(41, {'status': 'Delivered'})
        assert exc_info.value.status_code == 400
        assert "Invalid status transition" in exc_info.value.detail

    def test_delivery_blocks_when_unapproved_pick_list_discrepancies_exist(self):
        """Delivery is blocked if associated pick list has out-of-tolerance items not supervisor approved."""
        order = self.order_repo.create({
            'id': 42,
            'order_number': 'SO-042',
            'customer_id': 1,
            'status': 'Shipped',
            'grand_total': 100.0,
        })
        pl = self.pl_repo.create({
            'id': 501,
            'sales_order_id': 42,
        })
        self.pli_repo.create({
            'id': 601,
            'pick_list_id': 501,
            'product_name': 'Provolone Wheel',
            'tolerance_status': 'Out of Tolerance',
            'supervisor_approved': False,
        })

        with pytest.raises(HTTPException) as exc_info:
            self.service.update(42, {'status': 'Delivered'})
        assert exc_info.value.status_code == 400
        assert "Unapproved catch-weight tolerance discrepancies" in exc_info.value.detail
