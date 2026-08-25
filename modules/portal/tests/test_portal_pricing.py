import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from modules.portal.repositories.portal_repo import PortalRepository
from modules.portal.services.portal_pricing_service import PortalPricingService
from modules.portal.models.portal import (
    PortalCatalogQuery,
    PortalCatalogResponse,
    PortalAccountSummary,
    PortalCustomerProfile,
)


class TestPortalRepositoryPricing:
    """Unit tests for PortalRepository contracted pricing and catalog query methods."""

    @pytest.fixture
    def repo(self):
        return PortalRepository()

    def test_resolve_contracted_price_with_price_list_match(self, repo):
        customer = {
            "id": 10,
            "name": "Bistro Gourmet",
            "default_price_list_id": 5,
            "business_id": 1,
        }
        product = {
            "id": 101,
            "name": "Olive Oil Extra Virgin 5L",
            "sku": "OIL-EV-5L",
            "price": 50.0,
        }
        price_items = {
            101: {"unit_price": 42.50, "min_qty": 1, "product_id": 101}
        }

        with patch.object(repo, "get_customer", return_value=customer), \
             patch.object(repo, "get_product", return_value=product), \
             patch.object(repo, "get_price_list_items", return_value=price_items):

            res = repo.resolve_contracted_price(customer_id=10, product_id=101)

            assert res["product_id"] == 101
            assert res["base_price"] == 50.0
            assert res["contracted_price"] == 42.50
            assert res["unit_price"] == 42.50
            assert res["is_contracted"] is True
            assert res["discount_percent"] == 15.0  # (50 - 42.50) / 50 * 100

    def test_resolve_contracted_price_fallback_to_base_price_when_item_not_in_price_list(self, repo):
        customer = {
            "id": 10,
            "name": "Bistro Gourmet",
            "default_price_list_id": 5,
        }
        product = {
            "id": 102,
            "name": "Truffle Butter 500g",
            "sku": "TRUF-BUT-500",
            "price": 30.0,
        }
        price_items = {
            101: {"unit_price": 42.50, "product_id": 101}
        }

        with patch.object(repo, "get_customer", return_value=customer), \
             patch.object(repo, "get_product", return_value=product), \
             patch.object(repo, "get_price_list_items", return_value=price_items):

            res = repo.resolve_contracted_price(customer_id=10, product_id=102)

            assert res["product_id"] == 102
            assert res["base_price"] == 30.0
            assert res["contracted_price"] == 30.0
            assert res["unit_price"] == 30.0
            assert res["is_contracted"] is False
            assert res["discount_percent"] == 0.0

    def test_resolve_contracted_price_fallback_when_customer_has_no_price_list(self, repo):
        customer = {
            "id": 12,
            "name": "Corner Cafe",
            "default_price_list_id": None,
        }
        product = {
            "id": 103,
            "name": "Espresso Beans 1kg",
            "sku": "COF-ESP-1K",
            "price": 24.0,
        }

        with patch.object(repo, "get_customer", return_value=customer), \
             patch.object(repo, "get_product", return_value=product):

            res = repo.resolve_contracted_price(customer_id=12, product_id=103)

            assert res["product_id"] == 103
            assert res["base_price"] == 24.0
            assert res["contracted_price"] == 24.0
            assert res["is_contracted"] is False
            assert res["discount_percent"] == 0.0

    def test_get_catalog_with_contracted_prices_and_stock(self, repo):
        customer = {
            "id": 10,
            "name": "Bistro Gourmet",
            "default_price_list_id": 5,
            "min_order_amount": 150.0,
            "order_cutoff_time": "22:00:00",
        }
        price_items = {
            101: {"unit_price": 40.0, "product_id": 101}
        }
        stock_map = {101: 25.0, 102: 0.0}
        categories = [{"id": 1, "category_name": "Pantry", "item_count": 2}]

        mock_products = [
            {
                "id": 101,
                "name": "Olive Oil 5L",
                "sku": "OIL-5L",
                "barcode": "111222",
                "description": "Greek EVOO",
                "price": 50.0,
                "category": "Pantry",
                "base_uom_id": 1,
                "uom_name": "Bottle",
                "uom_code": "BTL",
                "image_url": "https://img/1.png",
                "is_active": True,
                "is_saleable": True,
            },
            {
                "id": 102,
                "name": "Flour 25kg",
                "sku": "FLOUR-25K",
                "barcode": "333444",
                "description": "Tipo 00",
                "price": 35.0,
                "category": "Pantry",
                "base_uom_id": 2,
                "uom_name": "Bag",
                "uom_code": "BAG",
                "image_url": None,
                "is_active": True,
                "is_saleable": True,
            },
        ]

        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = mock_products
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        with patch.object(repo, "get_customer", return_value=customer), \
             patch.object(repo, "get_price_list_items", return_value=price_items), \
             patch.object(repo, "get_stock_levels", return_value=stock_map), \
             patch.object(repo, "get_categories", return_value=categories):

            items, total, cats, meta = repo.get_catalog(
                customer_id=10,
                conn=mock_conn,
            )

            assert total == 2
            assert len(items) == 2

            # Product 101: has contracted price $40 (vs base $50, 20% off), in stock
            p1 = items[0]
            assert p1["id"] == 101
            assert p1["contracted_price"] == 40.0
            assert p1["is_contracted"] is True
            assert p1["discount_percent"] == 20.0
            assert p1["stock_qty"] == 25.0
            assert p1["is_in_stock"] is True

            # Product 102: no contracted price -> base price $35, out of stock
            p2 = items[1]
            assert p2["id"] == 102
            assert p2["contracted_price"] == 35.0
            assert p2["is_contracted"] is False
            assert p2["stock_qty"] == 0.0
            assert p2["is_in_stock"] is False

            assert meta["min_order_amount"] == 150.0
            assert meta["order_cutoff_time"] == "22:00:00"


class TestPortalPricingService:
    """Unit tests for PortalPricingService business logic and API model mapping."""

    @pytest.fixture
    def service(self):
        mock_repo = MagicMock(spec=PortalRepository)
        return PortalPricingService(repo=mock_repo)

    def test_get_catalog_service_mapping(self, service):
        service.repo.get_categories.return_value = [
            {"id": 1, "category_name": "Dairy", "item_count": 5}
        ]
        items_data = [
            {
                "id": 201,
                "product_code": "MILK-WHOLE-1G",
                "product_name": "Whole Milk 1 Gallon",
                "category_id": 1,
                "category_name": "Dairy",
                "uom_id": 3,
                "uom_name": "Gallon",
                "base_price": 5.50,
                "contracted_price": 4.80,
                "is_contracted": True,
                "discount_percent": 12.73,
                "stock_qty": 50.0,
                "is_in_stock": True,
                "image_url": "https://img/milk.jpg",
                "description": "Organic whole milk",
                "is_active": True,
            }
        ]
        service.repo.get_catalog.return_value = (
            items_data,
            1,
            [{"id": 1, "category_name": "Dairy", "item_count": 5}],
            {"min_order_amount": 100.0, "order_cutoff_time": "21:30:00"},
        )

        query = PortalCatalogQuery(category_id=1, search="milk", in_stock_only=True)
        response = service.get_catalog(customer_id=42, query=query)

        assert isinstance(response, PortalCatalogResponse)
        assert response.total == 1
        assert len(response.items) == 1
        item = response.items[0]
        assert item.id == 201
        assert item.product_code == "MILK-WHOLE-1G"
        assert item.contracted_price == 4.80
        assert item.is_contracted is True
        assert response.min_order_amount == 100.0
        assert response.order_cutoff_time == "21:30:00"

    def test_get_account_summary_success(self, service):
        service.repo.get_account_summary.return_value = {
            "customer_id": 42,
            "customer_name": "Trattoria Romana",
            "group_name": "Wholesale VIP",
            "email": "chef@trattoria.com",
            "phone": "555-0199",
            "credit_limit": 5000.0,
            "current_balance": 1200.0,
            "available_credit": 3800.0,
            "min_order_amount": 200.0,
            "order_cutoff_time": "22:00:00",
            "allow_reorders": True,
            "open_invoices_count": 2,
            "total_unpaid_amount": 1200.0,
            "recent_orders_count": 8,
            "default_price_list_id": 3,
            "default_price_list_name": "Preferred Tier A",
        }

        summary = service.get_account_summary(customer_id=42)

        assert isinstance(summary, PortalAccountSummary)
        assert summary.customer_id == 42
        assert summary.customer_name == "Trattoria Romana"
        assert summary.credit_limit == 5000.0
        assert summary.available_credit == 3800.0
        assert summary.open_invoices_count == 2
        assert summary.default_price_list_name == "Preferred Tier A"

    def test_get_account_summary_not_found_raises_404(self, service):
        service.repo.get_account_summary.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            service.get_account_summary(customer_id=999)

        assert exc_info.value.status_code == 404
        assert "Customer with id 999 not found" in str(exc_info.value.detail)

    def test_get_customer_profile_success(self, service):
        service.repo.get_customer.return_value = {
            "id": 42,
            "name": "Trattoria Romana",
            "group_name": "Wholesale VIP",
            "phone": "555-0199",
            "email": "chef@trattoria.com",
            "credit_limit": 5000.0,
            "balance": 1200.0,
            "min_order_amount": 200.0,
            "order_cutoff_time": "22:00:00",
            "allow_reorders": True,
            "default_price_list_id": 3,
            "default_tax_rate_id": 1,
            "payment_term_id": 2,
            "is_active": True,
        }

        profile = service.get_customer_profile(customer_id=42)

        assert isinstance(profile, PortalCustomerProfile)
        assert profile.id == 42
        assert profile.name == "Trattoria Romana"
        assert profile.available_credit == 3800.0
        assert profile.min_order_amount == 200.0
        assert profile.order_cutoff_time == "22:00:00"
        assert profile.allow_reorders is True

    def test_get_customer_profile_not_found_raises_404(self, service):
        service.repo.get_customer.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            service.get_customer_profile(customer_id=999)

        assert exc_info.value.status_code == 404
