import pytest
from unittest.mock import MagicMock, patch
from datetime import time
from modules.portal.repositories.portal_repo import PortalRepository
from modules.portal.services.portal_pricing_service import PortalPricingService
from modules.portal.models.portal import (
    PortalCustomerProfile,
    PortalAccountSummary,
    PortalCatalogQuery,
    PortalCatalogResponse,
)


@pytest.fixture
def mock_db():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value = mock_context

    with patch('modules.portal.repositories.portal_repo.get_connection', return_value=mock_conn), \
         patch('modules.portal.repositories.portal_repo.release_connection'):
        yield {'conn': mock_conn, 'cursor': mock_cursor, 'ctx': mock_context}


class TestPortalRepository:
    def test_get_customer_by_id_found(self, mock_db):
        repo = PortalRepository()
        mock_db['cursor'].fetchone.return_value = {
            'id': 101,
            'name': 'Gourmet Bistro',
            'group_name': 'Wholesale',
            'phone': '555-0100',
            'email': 'buyer@gourmetbistro.com',
            'credit_limit': 10000.00,
            'balance': 2500.00,
            'min_order_amount': 250.00,
            'order_cutoff_time': time(22, 0),
            'allow_reorders': True,
            'default_price_list_id': 2,
            'default_tax_rate_id': 1,
            'payment_term_id': 3,
            'is_active': True
        }

        customer = repo.get_customer_by_id(101)
        assert customer is not None
        assert customer['id'] == 101
        assert customer['name'] == 'Gourmet Bistro'
        assert customer['credit_limit'] == 10000.00
        assert customer['balance'] == 2500.00
        assert customer['available_credit'] == 7500.00
        assert customer['min_order_amount'] == 250.00
        assert customer['order_cutoff_time'] == '22:00'
        assert customer['allow_reorders'] is True

    def test_get_customer_by_id_not_found(self, mock_db):
        repo = PortalRepository()
        mock_db['cursor'].fetchone.return_value = None

        customer = repo.get_customer_by_id(9999)
        assert customer is None

    def test_resolve_customer_price_list_id(self, mock_db):
        repo = PortalRepository()
        # Customer has default_price_list_id = 5
        mock_db['cursor'].fetchone.return_value = {
            'id': 102,
            'name': 'Cafe Central',
            'credit_limit': 5000.0,
            'balance': 0.0,
            'min_order_amount': 100.0,
            'order_cutoff_time': '20:00',
            'allow_reorders': True,
            'default_price_list_id': 5,
            'is_active': True
        }

        pl_id = repo.resolve_customer_price_list_id(102)
        assert pl_id == 5

    def test_resolve_customer_price_list_id_fallback_to_default(self, mock_db):
        repo = PortalRepository()
        # Customer without price list
        mock_db['cursor'].fetchone.side_effect = [
            {
                'id': 103,
                'name': 'Deli Market',
                'credit_limit': 1000.0,
                'balance': 0.0,
                'min_order_amount': 0.0,
                'order_cutoff_time': None,
                'allow_reorders': True,
                'default_price_list_id': None,
                'is_active': True
            },
            # Default price list lookup
            {
                'id': 1,
                'name': 'Standard Retail',
                'code': 'STD',
                'description': 'Default Price List',
                'currency': 'USD',
                'is_active': True,
                'is_default': True
            }
        ]

        pl_id = repo.resolve_customer_price_list_id(103)
        assert pl_id == 1

    def test_get_catalog_categories(self, mock_db):
        repo = PortalRepository()
        mock_db['cursor'].fetchall.return_value = [
            {'category_name': 'Dairy', 'item_count': 12},
            {'category_name': 'Produce', 'item_count': 35},
        ]

        cats = repo.get_catalog_categories()
        assert len(cats) == 2
        assert cats[0]['category_name'] == 'Dairy'
        assert cats[0]['item_count'] == 12
        assert cats[1]['category_name'] == 'Produce'
        assert cats[1]['item_count'] == 35

    def test_get_catalog_with_contracted_pricing(self, mock_db):
        repo = PortalRepository()
        # Setup mocks: customer fetch, count query, data query
        mock_db['cursor'].fetchone.side_effect = [
            # Customer lookup
            {
                'id': 101,
                'name': 'Gourmet Bistro',
                'credit_limit': 10000.0,
                'balance': 0.0,
                'min_order_amount': 200.0,
                'order_cutoff_time': '21:00',
                'allow_reorders': True,
                'default_price_list_id': 2,
                'is_active': True
            },
            # Count query
            {'total': 2}
        ]

        mock_db['cursor'].fetchall.return_value = [
            {
                'id': 1,
                'product_code': 'MILK-001',
                'product_name': 'Whole Milk 1 Gallon',
                'category_name': 'Dairy',
                'base_price': 5.00,
                'image_url': 'http://img/milk.png',
                'description': 'Fresh dairy milk',
                'is_active': True,
                'uom_id': 3,
                'uom_name': 'Gallon',
                'stock_qty': 45.0,
                'contracted_unit_price': 4.25  # 15% discount
            },
            {
                'id': 2,
                'product_code': 'EGGS-012',
                'product_name': 'Organic Eggs 12pk',
                'category_name': 'Dairy',
                'base_price': 6.00,
                'image_url': None,
                'description': 'Grade A organic eggs',
                'is_active': True,
                'uom_id': 4,
                'uom_name': 'Dozen',
                'stock_qty': 0.0,
                'contracted_unit_price': None  # No contracted price, fallback to base
            }
        ]

        items, total = repo.get_catalog(customer_id=101, category='Dairy', page=1, limit=50)
        assert total == 2
        assert len(items) == 2

        # Item 1: Contracted price applied
        item1 = items[0]
        assert item1['id'] == 1
        assert item1['product_code'] == 'MILK-001'
        assert item1['base_price'] == 5.00
        assert item1['contracted_price'] == 4.25
        assert item1['is_contracted'] is True
        assert item1['discount_percent'] == 15.0
        assert item1['stock_qty'] == 45.0
        assert item1['is_in_stock'] is True

        # Item 2: Base price fallback
        item2 = items[1]
        assert item2['id'] == 2
        assert item2['base_price'] == 6.00
        assert item2['contracted_price'] == 6.00
        assert item2['is_contracted'] is False
        assert item2['discount_percent'] == 0.0
        assert item2['stock_qty'] == 0.0
        assert item2['is_in_stock'] is False

    def test_resolve_product_price_contracted(self, mock_db):
        repo = PortalRepository()
        mock_db['cursor'].fetchone.side_effect = [
            # Product lookup from T0003
            {'id': 10, 'name': 'Butter 1lb', 'sku': 'BUTTER-01', 'price': 8.00, 'is_active': True},
            # Price list item from T0084
            {'unit_price': 6.40, 'min_qty': 5}
        ]

        result = repo.resolve_product_price(product_id=10, price_list_id=2)
        assert result is not None
        assert result['product_id'] == 10
        assert result['base_price'] == 8.00
        assert result['contracted_price'] == 6.40
        assert result['unit_price'] == 6.40
        assert result['is_contracted'] is True
        assert result['discount_percent'] == 20.0
        assert result['min_qty'] == 5.0

    def test_resolve_product_price_base_fallback(self, mock_db):
        repo = PortalRepository()
        mock_db['cursor'].fetchone.side_effect = [
            # Product lookup from T0003
            {'id': 11, 'name': 'Cheese 1lb', 'sku': 'CHEESE-01', 'price': 12.00, 'is_active': True},
            # T0084 returns None
            None
        ]

        result = repo.resolve_product_price(product_id=11, price_list_id=2)
        assert result is not None
        assert result['product_id'] == 11
        assert result['base_price'] == 12.00
        assert result['contracted_price'] == 12.00
        assert result['unit_price'] == 12.00
        assert result['is_contracted'] is False
        assert result['discount_percent'] == 0.0

    def test_get_account_summary(self, mock_db):
        repo = PortalRepository()
        mock_db['cursor'].fetchone.side_effect = [
            # Customer lookup
            {
                'id': 200,
                'name': 'Trattoria Bella',
                'group_name': 'Restaurant',
                'email': 'bella@trattoria.com',
                'phone': '555-4321',
                'credit_limit': 15000.0,
                'balance': 3000.0,
                'available_credit': 12000.0,
                'min_order_amount': 300.0,
                'order_cutoff_time': '22:00',
                'allow_reorders': True,
                'default_price_list_id': 3,
                'is_active': True
            },
            # Price list lookup
            {
                'id': 3,
                'name': 'VIP Wholesale Tier'
            },
            # Invoices aggregation
            {
                'open_count': 3,
                'total_unpaid': 3000.0
            },
            # Orders aggregation
            {
                'order_count': 14
            }
        ]

        summary = repo.get_account_summary(200)
        assert summary['customer_id'] == 200
        assert summary['customer_name'] == 'Trattoria Bella'
        assert summary['credit_limit'] == 15000.0
        assert summary['current_balance'] == 3000.0
        assert summary['available_credit'] == 12000.0
        assert summary['open_invoices_count'] == 3
        assert summary['total_unpaid_amount'] == 3000.0
        assert summary['recent_orders_count'] == 14
        assert summary['default_price_list_name'] == 'VIP Wholesale Tier'


class TestPortalPricingService:
    def test_get_customer_profile(self):
        mock_repo = MagicMock()
        mock_repo.get_customer_by_id.return_value = {
            'id': 105,
            'name': 'Artisan Bakery',
            'group_name': 'Bakery',
            'phone': '555-8888',
            'email': 'baker@artisan.com',
            'credit_limit': 8000.0,
            'balance': 1200.0,
            'available_credit': 6800.0,
            'min_order_amount': 150.0,
            'order_cutoff_time': '21:30',
            'allow_reorders': True,
            'default_price_list_id': 4,
            'default_tax_rate_id': 1,
            'payment_term_id': 2,
            'is_active': True
        }

        service = PortalPricingService(portal_repo=mock_repo)
        profile = service.get_customer_profile(105)

        assert isinstance(profile, PortalCustomerProfile)
        assert profile.id == 105
        assert profile.name == 'Artisan Bakery'
        assert profile.min_order_amount == 150.0
        assert profile.order_cutoff_time == '21:30'

    def test_get_account_summary(self):
        mock_repo = MagicMock()
        mock_repo.get_account_summary.return_value = {
            'customer_id': 105,
            'customer_name': 'Artisan Bakery',
            'group_name': 'Bakery',
            'email': 'baker@artisan.com',
            'phone': '555-8888',
            'credit_limit': 8000.0,
            'current_balance': 1200.0,
            'available_credit': 6800.0,
            'min_order_amount': 150.0,
            'order_cutoff_time': '21:30',
            'allow_reorders': True,
            'open_invoices_count': 2,
            'total_unpaid_amount': 1200.0,
            'recent_orders_count': 9,
            'default_price_list_id': 4,
            'default_price_list_name': 'Bakery Special'
        }

        service = PortalPricingService(portal_repo=mock_repo)
        summary = service.get_account_summary(105)

        assert isinstance(summary, PortalAccountSummary)
        assert summary.customer_id == 105
        assert summary.open_invoices_count == 2
        assert summary.total_unpaid_amount == 1200.0

    def test_get_catalog(self):
        mock_repo = MagicMock()
        mock_repo.get_customer_by_id.return_value = {
            'id': 101,
            'min_order_amount': 200.0,
            'order_cutoff_time': '22:00'
        }
        mock_repo.get_catalog_categories.return_value = [
            {'id': 1, 'category_name': 'Flour & Grains', 'item_count': 5}
        ]
        mock_repo.get_catalog.return_value = (
            [
                {
                    'id': 50,
                    'product_code': 'FLOUR-50',
                    'product_name': 'Bread Flour 50lb',
                    'category_id': None,
                    'category_name': 'Flour & Grains',
                    'uom_id': 1,
                    'uom_name': 'Bag',
                    'base_price': 30.0,
                    'contracted_price': 24.0,
                    'is_contracted': True,
                    'discount_percent': 20.0,
                    'stock_qty': 100.0,
                    'is_in_stock': True,
                    'image_url': None,
                    'description': 'High protein bread flour',
                    'is_active': True
                }
            ],
            1
        )

        service = PortalPricingService(portal_repo=mock_repo)
        response = service.get_catalog(customer_id=101, query=PortalCatalogQuery(category_id=1))

        assert isinstance(response, PortalCatalogResponse)
        assert response.total == 1
        assert len(response.items) == 1
        assert response.items[0].product_name == 'Bread Flour 50lb'
        assert response.items[0].contracted_price == 24.0
        assert response.min_order_amount == 200.0
        assert response.order_cutoff_time == '22:00'

    def test_resolve_line_items_pricing(self):
        mock_repo = MagicMock()
        mock_repo.get_contracted_prices_for_products.return_value = {
            50: {
                'product_id': 50,
                'product_code': 'FLOUR-50',
                'product_name': 'Bread Flour 50lb',
                'unit_price': 25.0,
                'base_price': 30.0,
                'is_contracted': True,
                'discount_percent': 16.67
            },
            51: {
                'product_id': 51,
                'product_code': 'YEAST-01',
                'product_name': 'Instant Dry Yeast 1lb',
                'unit_price': 10.0,
                'base_price': 10.0,
                'is_contracted': False,
                'discount_percent': 0.0
            }
        }

        service = PortalPricingService(portal_repo=mock_repo)
        input_items = [
            {'product_id': 50, 'qty': 4, 'notes': 'Stack carefully'},
            {'product_id': 51, 'qty': 2}
        ]

        lines = service.resolve_line_items_pricing(customer_id=101, items=input_items)
        assert len(lines) == 2

        assert lines[0]['product_id'] == 50
        assert lines[0]['qty'] == 4.0
        assert lines[0]['unit_price'] == 25.0
        assert lines[0]['line_total'] == 100.0
        assert lines[0]['is_contracted'] is True

        assert lines[1]['product_id'] == 51
        assert lines[1]['qty'] == 2.0
        assert lines[1]['unit_price'] == 10.0
        assert lines[1]['line_total'] == 20.0
        assert lines[1]['is_contracted'] is False
