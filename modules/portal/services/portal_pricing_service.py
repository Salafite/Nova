import logging
from typing import Optional, List, Dict, Any
from modules.portal.repositories.portal_repo import PortalRepository
from modules.portal.models.portal import (
    PortalCustomerProfile,
    PortalAccountSummary,
    PortalCatalogItem,
    PortalCatalogCategory,
    PortalCatalogQuery,
    PortalCatalogResponse,
)

logger = logging.getLogger(__name__)


class PortalPricingService:
    """Service layer for B2B Customer Portal catalog browsing, contracted pricing resolution, and account metrics."""

    def __init__(self, portal_repo: Optional[PortalRepository] = None):
        self.portal_repo = portal_repo or PortalRepository()

    def get_customer_profile(self, customer_id: int) -> Optional[PortalCustomerProfile]:
        """Retrieve customer profile and B2B ordering configuration."""
        raw = self.portal_repo.get_customer_by_id(customer_id)
        if not raw:
            return None
        return PortalCustomerProfile(**raw)

    def get_account_summary(self, customer_id: int) -> PortalAccountSummary:
        """Retrieve customer dashboard account overview."""
        summary = self.portal_repo.get_account_summary(customer_id)
        return PortalAccountSummary(**summary)

    def get_categories(self) -> List[PortalCatalogCategory]:
        """List distinct active catalog categories."""
        raw_cats = self.portal_repo.get_catalog_categories()
        return [PortalCatalogCategory(**cat) for cat in raw_cats]

    def get_catalog(
        self,
        customer_id: int,
        query: Optional[PortalCatalogQuery] = None
    ) -> PortalCatalogResponse:
        """Fetch paginated catalog with customer-specific contracted prices and stock status."""
        query = query or PortalCatalogQuery()
        customer = self.portal_repo.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist.")

        categories = self.get_categories()

        # Resolve category name filter if category_id integer was provided
        category_name: Optional[str] = None
        if query.category_id is not None:
            for cat in categories:
                if cat.id == query.category_id:
                    category_name = cat.category_name
                    break

        items_raw, total = self.portal_repo.get_catalog(
            customer_id=customer_id,
            category=category_name,
            search=query.search,
            in_stock_only=query.in_stock_only,
            page=query.page,
            limit=query.limit
        )

        catalog_items = [PortalCatalogItem(**item) for item in items_raw]

        return PortalCatalogResponse(
            items=catalog_items,
            total=total,
            page=query.page,
            limit=query.limit,
            categories=categories,
            min_order_amount=customer.get('min_order_amount', 0.0),
            order_cutoff_time=customer.get('order_cutoff_time')
        )

    def resolve_product_price(self, customer_id: int, product_id: int) -> Dict[str, Any]:
        """Resolve unit price for a single product for a customer."""
        resolved = self.portal_repo.resolve_product_price(product_id=product_id, customer_id=customer_id)
        if not resolved:
            raise ValueError(f"Product with ID {product_id} not found.")
        return resolved

    def resolve_line_items_pricing(
        self,
        customer_id: int,
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate line totals and savings across multiple order items using contracted prices.
        
        Input items: [{'product_id': 10, 'qty': 5, 'notes': 'optional'}]
        Output items: [{'product_id': 10, 'product_name': '...', 'product_code': '...', 'qty': 5, 'unit_price': 12.0, 'base_price': 15.0, 'line_total': 60.0, 'is_contracted': True, 'discount_percent': 20.0}]
        """
        if not items:
            return []

        product_ids = [item['product_id'] for item in items if 'product_id' in item]
        price_map = self.portal_repo.get_contracted_prices_for_products(product_ids, customer_id=customer_id)

        processed_lines = []
        for idx, item in enumerate(items, start=1):
            pid = item.get('product_id')
            qty = float(item.get('qty', 1))
            if qty <= 0:
                raise ValueError(f"Invalid quantity {qty} for product ID {pid}")

            pricing = price_map.get(pid)
            if not pricing:
                raise ValueError(f"Product ID {pid} not found or inactive")

            unit_price = float(pricing['unit_price'])
            base_price = float(pricing['base_price'])
            line_total = round(qty * unit_price, 2)

            processed_lines.append({
                'line_number': idx,
                'product_id': pid,
                'product_code': pricing.get('product_code', ''),
                'product_name': pricing.get('product_name', ''),
                'qty': qty,
                'unit_price': unit_price,
                'base_price': base_price,
                'line_total': line_total,
                'is_contracted': pricing.get('is_contracted', False),
                'discount_percent': pricing.get('discount_percent', 0.0),
                'notes': item.get('notes')
            })

        return processed_lines
