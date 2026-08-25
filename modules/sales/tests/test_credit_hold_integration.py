import pytest
from datetime import date
from unittest.mock import MagicMock

from modules.sales.services.sales_service import SalesOrderService
from modules.sales.services.enhanced_sales_order_service import EnhancedSalesOrderService
from modules.sales.services.credit_service import CreditService


class TestSalesOrderCreditHoldIntegration:
    @pytest.fixture
    def mock_repos(self):
        order_repo = MagicMock()
        line_repo = MagicMock()
        cust_repo = MagicMock()
        inv_repo = MagicMock()
        pl_repo = MagicMock()
        pli_repo = MagicMock()
        product_repo = MagicMock()

        orders = {}
        lines = {}

        def mock_order_create(payload, conn=None):
            new_id = len(orders) + 1
            rec = dict(payload)
            rec['id'] = new_id
            orders[new_id] = rec
            return dict(rec)

        def mock_order_get(id_val, conn=None):
            return dict(orders[id_val]) if id_val in orders else None

        def mock_order_update(id_val, payload, conn=None):
            if id_val in orders:
                orders[id_val].update(payload)
                return dict(orders[id_val])
            return None

        def mock_line_create(payload, conn=None):
            new_id = len(lines) + 1
            rec = dict(payload)
            rec['id'] = new_id
            lines[new_id] = rec
            return dict(rec)

        order_repo.create.side_effect = mock_order_create
        order_repo.get.side_effect = mock_order_get
        order_repo.update.side_effect = mock_order_update
        line_repo.create.side_effect = mock_line_create

        return {
            'order_repo': order_repo,
            'line_repo': line_repo,
            'cust_repo': cust_repo,
            'inv_repo': inv_repo,
            'pl_repo': pl_repo,
            'pli_repo': pli_repo,
            'product_repo': product_repo,
            'orders': orders,
            'lines': lines,
        }

    def test_sales_order_create_within_credit_limit(self, mock_repos):
        cust_repo = mock_repos['cust_repo']
        inv_repo = mock_repos['inv_repo']

        cust_repo.get.return_value = {
            'id': 1,
            'name': 'Good Standing Customer',
            'credit_limit': 10000.00,
            'balance': 2000.00,
        }
        inv_repo.list.return_value = []

        credit_svc = CreditService(customer_repo=cust_repo, invoice_repo=inv_repo, order_repo=mock_repos['order_repo'])
        sales_svc = SalesOrderService(
            repo=mock_repos['order_repo'],
            line_repo=mock_repos['line_repo'],
            customer_repo=cust_repo,
            inv_repo=inv_repo,
            credit_service=credit_svc,
        )

        order = sales_svc.create({
            'order_number': 'SO-001',
            'customer_id': 1,
            'subtotal': 1000.00,
            'tax': 100.00,
            'grand_total': 1100.00,
        })

        assert order['status'] == 'Pending'
        assert order.get('hold_reason') is None

    def test_sales_order_create_exceeding_credit_limit_places_on_hold(self, mock_repos):
        cust_repo = mock_repos['cust_repo']
        inv_repo = mock_repos['inv_repo']

        cust_repo.get.return_value = {
            'id': 2,
            'name': 'Over-Limit Customer',
            'credit_limit': 5000.00,
            'balance': 4500.00,
        }
        inv_repo.list.return_value = []

        credit_svc = CreditService(customer_repo=cust_repo, invoice_repo=inv_repo, order_repo=mock_repos['order_repo'])
        sales_svc = SalesOrderService(
            repo=mock_repos['order_repo'],
            line_repo=mock_repos['line_repo'],
            customer_repo=cust_repo,
            inv_repo=inv_repo,
            credit_service=credit_svc,
        )

        # 4500 + 1000 = 5500 > 5000 limit
        order = sales_svc.create({
            'order_number': 'SO-002',
            'customer_id': 2,
            'subtotal': 900.00,
            'tax': 100.00,
            'grand_total': 1000.00,
        })

        assert order['status'] == 'Credit Hold'
        assert 'Customer credit limit exceeded' in order['hold_reason']
        assert '$5,500.00 > Limit $5,000.00' in order['hold_reason']

    def test_sales_order_create_with_overdue_invoices_places_on_hold(self, mock_repos):
        cust_repo = mock_repos['cust_repo']
        inv_repo = mock_repos['inv_repo']

        cust_repo.get.return_value = {
            'id': 3,
            'name': 'Delinquent Invoices Customer',
            'credit_limit': 50000.00,
            'balance': 500.00,
        }
        # Unpaid invoice due 60 days ago
        inv_repo.list.return_value = [
            {
                'id': 10,
                'invoice_number': 'INV-OLD-01',
                'partner_id': 3,
                'issue_date': '2026-05-01',
                'due_date': '2026-06-01',
                'total_amount': 2500.00,
                'status': 'Issued',
            }
        ]

        credit_svc = CreditService(customer_repo=cust_repo, invoice_repo=inv_repo, order_repo=mock_repos['order_repo'])
        sales_svc = SalesOrderService(
            repo=mock_repos['order_repo'],
            line_repo=mock_repos['line_repo'],
            customer_repo=cust_repo,
            inv_repo=inv_repo,
            credit_service=credit_svc,
        )

        order = sales_svc.create({
            'order_number': 'SO-003',
            'customer_id': 3,
            'subtotal': 300.00,
            'tax': 30.00,
            'grand_total': 330.00,
        })

        assert order['status'] == 'Credit Hold'
        assert 'overdue by >30 days' in order['hold_reason']
        assert '$2,500.00' in order['hold_reason']

    def test_sales_order_create_both_limit_and_overdue_reasons(self, mock_repos):
        cust_repo = mock_repos['cust_repo']
        inv_repo = mock_repos['inv_repo']

        cust_repo.get.return_value = {
            'id': 4,
            'name': 'Severely Delinquent Customer',
            'credit_limit': 1000.00,
            'balance': 900.00,
        }
        inv_repo.list.return_value = [
            {
                'id': 20,
                'invoice_number': 'INV-OLD-02',
                'partner_id': 4,
                'issue_date': '2026-05-01',
                'due_date': '2026-06-01',
                'total_amount': 800.00,
                'status': 'Issued',
            }
        ]

        credit_svc = CreditService(customer_repo=cust_repo, invoice_repo=inv_repo, order_repo=mock_repos['order_repo'])
        sales_svc = SalesOrderService(
            repo=mock_repos['order_repo'],
            line_repo=mock_repos['line_repo'],
            customer_repo=cust_repo,
            inv_repo=inv_repo,
            credit_service=credit_svc,
        )

        order = sales_svc.create({
            'order_number': 'SO-004',
            'customer_id': 4,
            'subtotal': 500.00,
            'tax': 50.00,
            'grand_total': 550.00,
        })

        assert order['status'] == 'Credit Hold'
        assert 'Customer credit limit exceeded' in order['hold_reason']
        assert 'Customer has 1 invoice overdue by >30 days' in order['hold_reason']

    def test_enhanced_sales_order_create_with_lines_credit_hold(self, mock_repos):
        cust_repo = mock_repos['cust_repo']
        inv_repo = mock_repos['inv_repo']
        price_list_repo = MagicMock()
        tax_rate_repo = MagicMock()

        cust_repo.get.return_value = {
            'id': 5,
            'name': 'Enhanced Order Customer',
            'credit_limit': 3000.00,
            'balance': 2000.00,
        }
        inv_repo.list.return_value = []
        tax_rate_repo.get.return_value = {'id': 1, 'rate': 10.0}

        credit_svc = CreditService(customer_repo=cust_repo, invoice_repo=inv_repo, order_repo=mock_repos['order_repo'])
        enhanced_svc = EnhancedSalesOrderService(
            repo=mock_repos['order_repo'],
            line_repo=mock_repos['line_repo'],
            price_list_item_repo=price_list_repo,
            tax_rate_repo=tax_rate_repo,
            customer_repo=cust_repo,
            inv_repo=inv_repo,
            credit_service=credit_svc,
        )

        # 2 lines: line1 = 2 * $600 = $1200, line2 = 1 * $200 = $200 -> subtotal = $1400, tax 10% = $140 -> grand_total = $1540
        # Customer balance 2000 + 1540 = 3540 > 3000 limit
        result = enhanced_svc.create_with_lines(
            order_data={
                'order_number': 'SO-ENH-001',
                'customer_id': 5,
                'tax_rate_id': 1,
            },
            lines=[
                {'product_id': 101, 'product_name': 'Item A', 'qty': 2, 'unit_price': 600.0},
                {'product_id': 102, 'product_name': 'Item B', 'qty': 1, 'unit_price': 200.0},
            ]
        )

        assert result['status'] == 'Credit Hold'
        assert result['subtotal'] == 1400.0
        assert result['tax'] == 140.0
        assert result['grand_total'] == 1540.0
        assert 'Customer credit limit exceeded' in result['hold_reason']
        assert '$3,540.00 > Limit $3,000.00' in result['hold_reason']

    def test_enhanced_sales_order_create_with_lines_clean_customer(self, mock_repos):
        cust_repo = mock_repos['cust_repo']
        inv_repo = mock_repos['inv_repo']
        price_list_repo = MagicMock()
        tax_rate_repo = MagicMock()

        cust_repo.get.return_value = {
            'id': 6,
            'name': 'Clean Enhanced Customer',
            'credit_limit': 10000.00,
            'balance': 1000.00,
        }
        inv_repo.list.return_value = []
        tax_rate_repo.get.return_value = {'id': 1, 'rate': 5.0}

        credit_svc = CreditService(customer_repo=cust_repo, invoice_repo=inv_repo, order_repo=mock_repos['order_repo'])
        enhanced_svc = EnhancedSalesOrderService(
            repo=mock_repos['order_repo'],
            line_repo=mock_repos['line_repo'],
            price_list_item_repo=price_list_repo,
            tax_rate_repo=tax_rate_repo,
            customer_repo=cust_repo,
            inv_repo=inv_repo,
            credit_service=credit_svc,
        )

        result = enhanced_svc.create_with_lines(
            order_data={
                'order_number': 'SO-ENH-002',
                'customer_id': 6,
                'tax_rate_id': 1,
            },
            lines=[
                {'product_id': 101, 'product_name': 'Item A', 'qty': 1, 'unit_price': 500.0},
            ]
        )

        assert result['status'] == 'Pending'
        assert result['subtotal'] == 500.0
        assert result['tax'] == 25.0
        assert result['grand_total'] == 525.0
        assert result.get('hold_reason') is None
