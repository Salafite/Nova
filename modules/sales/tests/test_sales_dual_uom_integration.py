import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from modules.sales.services.sales_service import SalesOrderService
from modules.sales.controllers import T0012I


class InMemoryRepo:
    """In-memory CRUD repository for sales dual UOM integration tests."""
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


class TestSalesDualUOMIntegration:
    """Integration tests for Sales Order dual UOM pricing, recalculation, delivery gating and invoice generation."""

    def setup_method(self):
        self.customers = [
            {
                'id': 200,
                'name': 'Gourmet Deli Corp',
                'credit_limit': 10000.0,
                'balance': 1500.0,
            },
            {
                'id': 201,
                'name': 'Low Credit Limit Market',
                'credit_limit': 2000.0,
                'balance': 1800.0,
            },
        ]

        self.products = [
            {
                'id': 101,
                'name': 'Parmigiano Reggiano Wheel',
                'sku': 'PARM-40KG',
                'is_catch_weight': True,
                'pricing_uom_id': 2,
                'nominal_weight': 40.0,
                'tolerance_pct': 5.0,
                'price': 600.0,
            },
            {
                'id': 102,
                'name': 'Gouda Cheese Wheel',
                'sku': 'GOUDA-20KG',
                'is_catch_weight': True,
                'pricing_uom_id': 2,
                'nominal_weight': 20.0,
                'tolerance_pct': 5.0,
                'price': 300.0,
            },
            {
                'id': 103,
                'name': 'Balsamic Vinegar 500ml',
                'sku': 'VIN-500ML',
                'is_catch_weight': False,
                'nominal_weight': None,
                'price': 25.0,
            },
        ]

        self.order_repo = InMemoryRepo('T0012')
        self.line_repo = InMemoryRepo('T0013')
        self.customer_repo = InMemoryRepo('T0010', self.customers)
        self.inv_repo = InMemoryRepo('T0090')
        self.pl_repo = InMemoryRepo('T0101')
        self.pli_repo = InMemoryRepo('T0102')
        self.product_repo = InMemoryRepo('T0003', self.products)

        self.service = SalesOrderService(
            repo=self.order_repo,
            line_repo=self.line_repo,
            customer_repo=self.customer_repo,
            inv_repo=self.inv_repo,
            pl_repo=self.pl_repo,
            pli_repo=self.pli_repo,
            product_repo=self.product_repo,
        )

    def test_create_sales_order_with_dual_uom_lines(self):
        """Test creating a sales order with dual UOM items and verifying credit limit."""
        order = self.service.create({
            'order_number': 'SO-9001',
            'customer_id': 200,
            'warehouse_id': 1,
            'subtotal': 1200.0,
            'tax': 60.0,
            'grand_total': 1260.0,
            'status': 'Pending',
            'order_date': date(2026, 8, 24),
        })

        line1 = self.line_repo.create({
            'sales_order_id': order['id'],
            'product_id': 101,
            'product_name': 'Parmigiano Reggiano Wheel',
            'qty': 2.0,  # 2 wheels = 80kg nominal
            'unit_price': 600.0,
            'line_total': 1200.0,
            'is_catch_weight': True,
            'pricing_uom_id': 2,
            'unit_price_pricing_uom': 15.0,
            'nominal_weight': 80.0,
            'line_number': 1,
        })

        assert order['id'] is not None
        assert order['status'] == 'Pending'
        assert line1['nominal_weight'] == 80.0
        assert line1['unit_price_pricing_uom'] == 15.0

    def test_create_sales_order_credit_limit_exceeded_places_on_credit_hold(self):
        """Creating an order that pushes balance over credit limit automatically sets status to Credit Hold."""
        # Customer 201 has balance 1800 and credit limit 2000 (room for 200)
        order = self.service.create({
            'order_number': 'SO-9002',
            'customer_id': 201,
            'warehouse_id': 1,
            'subtotal': 500.0,
            'tax': 0.0,
            'grand_total': 500.0,
            'status': 'Pending',
        })
        assert order['status'] == 'Credit Hold'
        assert 'Customer credit limit exceeded' in order['hold_reason']
        assert '$2,300.00 > Limit $2,000.00' in order['hold_reason']

    def test_delivery_validation_blocks_when_pick_list_has_unapproved_discrepancies(self):
        """Delivering an order is blocked if associated pick list has unapproved out-of-tolerance items."""
        order = self.order_repo.create({
            'id': 100,
            'order_number': 'SO-100',
            'customer_id': 200,
            'warehouse_id': 1,
            'status': 'Shipped',
            'subtotal': 1200.0,
            'grand_total': 1200.0,
            'order_date': date(2026, 8, 24),
        })
        line = self.line_repo.create({
            'id': 1001,
            'sales_order_id': 100,
            'product_id': 101,
            'qty': 2.0,
            'unit_price': 600.0,
            'line_total': 1200.0,
            'is_catch_weight': True,
            'unit_price_pricing_uom': 15.0,
            'nominal_weight': 80.0,
        })
        pkl = self.pl_repo.create({
            'id': 501,
            'sales_order_id': 100,
            'status': 'In Progress',
        })
        self.pli_repo.create({
            'id': 701,
            'pick_list_id': 501,
            'sales_order_line_id': 1001,
            'product_name': 'Parmigiano Reggiano Wheel',
            'nominal_weight': 80.0,
            'catch_weight_actual': 92.0,  # +15% out of tolerance
            'tolerance_pct': 5.0,
            'tolerance_status': 'Out of Tolerance',
            'supervisor_approved': False,
        })

        # Attempt to deliver: must fail
        with pytest.raises(HTTPException) as exc_info:
            self.service.update(100, {'status': 'Delivered'})

        assert exc_info.value.status_code == 400
        assert "Unapproved catch-weight tolerance discrepancies exist" in exc_info.value.detail

        # Order status remains Shipped
        assert self.order_repo.get(100)['status'] == 'Shipped'

    def test_delivery_succeeds_after_approval_and_recalculates_pricing(self):
        """After supervisor approves out-of-tolerance item, delivery succeeds, recalculates price, and creates invoice."""
        order = self.order_repo.create({
            'id': 101,
            'order_number': 'SO-101',
            'customer_id': 200,
            'warehouse_id': 1,
            'status': 'Shipped',
            'subtotal': 1200.0,
            'tax': 60.0,  # 5% tax
            'grand_total': 1260.0,
            'order_date': date(2026, 8, 24),
        })
        line = self.line_repo.create({
            'id': 1002,
            'sales_order_id': 101,
            'product_id': 101,
            'qty': 2.0,
            'unit_price': 600.0,
            'line_total': 1200.0,
            'is_catch_weight': True,
            'unit_price_pricing_uom': 15.0,
            'nominal_weight': 80.0,
        })
        pkl = self.pl_repo.create({
            'id': 502,
            'sales_order_id': 101,
            'status': 'Completed',
        })
        self.pli_repo.create({
            'id': 702,
            'pick_list_id': 502,
            'sales_order_line_id': 1002,
            'product_name': 'Parmigiano Reggiano Wheel',
            'nominal_weight': 80.0,
            'catch_weight_actual': 84.0,  # +5% overweight (84kg * $15 = $1260)
            'tolerance_pct': 5.0,
            'tolerance_status': 'Approved',
            'supervisor_approved': True,
            'supervisor_approved_by': 99,
        })

        with patch.object(self.service, '_generate_invoice_number', return_value='INV-90001'):
            self.service.update(101, {'status': 'Delivered'})

        # Verify order status and recalculated amounts
        updated_order = self.order_repo.get(101)
        assert updated_order['status'] == 'Delivered'
        assert updated_order['subtotal'] == 1260.0  # 84.0 * 15.0
        assert updated_order['tax'] == 63.0  # 5% of 1260
        assert updated_order['grand_total'] == 1323.0  # 1260 + 63

        # Verify line updated
        updated_line = self.line_repo.get(1002)
        assert updated_line['catch_weight_actual'] == 84.0
        assert updated_line['recalculated_total'] == 1260.0

        # Verify invoice created with catch-weight attributes
        invoices = self.inv_repo.list(filters={'sales_order_id': 101})
        assert len(invoices) == 1
        inv = invoices[0]
        assert inv['invoice_number'] == 'INV-90001'
        assert inv['total_amount'] == 1323.0
        assert inv['is_catch_weight'] is True
        assert inv['nominal_total_weight'] == 80.0
        assert inv['actual_total_weight'] == 84.0
        assert inv['weight_adjustment_amount'] == 60.0
        assert 'Catch-weight adjustment: +60.00' in inv['notes']

        # Verify customer balance updated: 1500 + 1323 = 2823
        updated_cust = self.customer_repo.get(200)
        assert updated_cust['balance'] == 2823.0

    def test_multi_line_mixed_order_underweight_adjustment(self):
        """Mixed order with 1 catch-weight line (underweight) and 1 standard line."""
        order = self.order_repo.create({
            'id': 102,
            'order_number': 'SO-102',
            'customer_id': 200,
            'warehouse_id': 1,
            'status': 'Shipped',
            'subtotal': 1250.0,  # 1200 (cheese) + 50 (vinegar: 2 @ 25)
            'tax': 0.0,
            'grand_total': 1250.0,
            'order_date': date(2026, 8, 24),
        })
        line_cw = self.line_repo.create({
            'id': 1003,
            'sales_order_id': 102,
            'product_id': 101,
            'qty': 2.0,
            'unit_price': 600.0,
            'line_total': 1200.0,
            'is_catch_weight': True,
            'unit_price_pricing_uom': 15.0,
            'nominal_weight': 80.0,
            'catch_weight_actual': 76.0,  # Underweight: 76kg * $15 = $1140 (-$60)
        })
        line_std = self.line_repo.create({
            'id': 1004,
            'sales_order_id': 102,
            'product_id': 103,
            'qty': 2.0,
            'unit_price': 25.0,
            'line_total': 50.0,
            'is_catch_weight': False,
            'catch_weight_actual': None,
        })

        recalc = self.service.recalculate_order_catch_weight(102)

        assert recalc['is_catch_weight'] is True
        assert recalc['original_subtotal'] == 1250.0
        assert recalc['recalculated_subtotal'] == 1190.0  # 1140 + 50
        assert recalc['weight_adjustment_amount'] == -60.0
        assert recalc['nominal_total_weight'] == 80.0
        assert recalc['actual_total_weight'] == 76.0
        assert recalc['grand_total'] == 1190.0

        # Deliver order and verify invoice
        with patch.object(self.service, '_generate_invoice_number', return_value='INV-90002'):
            self.service.update(102, {'status': 'Delivered'})

        invoices = self.inv_repo.list(filters={'sales_order_id': 102})
        assert len(invoices) == 1
        inv = invoices[0]
        assert inv['total_amount'] == 1190.0
        assert inv['weight_adjustment_amount'] == -60.0
        assert 'Catch-weight adjustment: -60.00' in inv['notes']
