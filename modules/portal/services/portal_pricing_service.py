import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from modules.portal.repositories.portal_repo import PortalRepository
from modules.portal.models.portal import (
    PortalCatalogItem,
    PortalCatalogCategory,
    PortalCatalogQuery,
    PortalCatalogResponse,
    PortalAccountSummary,
    PortalCustomerProfile,
)

logger = logging.getLogger(__name__)


class PortalPricingService:
    """Service to resolve customer-specific contracted pricing, catalog search, and account balances."""

    def __init__(self, repo: Optional[PortalRepository] = None):
        self.repo = repo or PortalRepository()

    def get_catalog(
        self,
        customer_id: int,
        query: Optional[PortalCatalogQuery] = None,
        conn=None,
    ) -> PortalCatalogResponse:
        """Query product catalog with personalized contracted pricing and stock availability."""
        if query is None:
            query = PortalCatalogQuery()

        category_name = None
        if query.category_id is not None:
            # Check if category_id represents a category name or index
            categories = self.repo.get_categories(conn=conn)
            for cat in categories:
                if cat["id"] == query.category_id:
                    category_name = cat["category_name"]
                    break

        items, total, raw_categories, cust_meta = self.repo.get_catalog(
            customer_id=customer_id,
            category=category_name,
            search=query.search,
            in_stock_only=query.in_stock_only,
            page=query.page,
            limit=query.limit,
            conn=conn,
        )

        catalog_items = [PortalCatalogItem(**item) for item in items]
        category_items = [PortalCatalogCategory(**cat) for cat in raw_categories]

        return PortalCatalogResponse(
            items=catalog_items,
            total=total,
            page=query.page,
            limit=query.limit,
            categories=category_items,
            min_order_amount=cust_meta.get("min_order_amount", 0.0),
            order_cutoff_time=cust_meta.get("order_cutoff_time"),
        )

    def resolve_unit_price(
        self,
        customer_id: int,
        product_id: int,
        qty: float = 1.0,
        conn=None,
    ) -> Dict[str, Any]:
        """Resolve unit price for product under customer's contracted price list or product base price."""
        return self.repo.resolve_contracted_price(
            customer_id=customer_id,
            product_id=product_id,
            qty=qty,
            conn=conn,
        )

    def get_account_summary(
        self,
        customer_id: int,
        conn=None,
    ) -> PortalAccountSummary:
        """Retrieve customer account overview with credit metrics, unpaid invoices, and order counts."""
        summary = self.repo.get_account_summary(customer_id, conn=conn)
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with id {customer_id} not found",
            )
        return PortalAccountSummary(**summary)

    def get_customer_profile(
        self,
        customer_id: int,
        conn=None,
    ) -> PortalCustomerProfile:
        """Retrieve customer profile and portal settings."""
        customer = self.repo.get_customer(customer_id, conn=conn)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with id {customer_id} not found",
            )
        credit_limit = float(customer.get("credit_limit") or 0.0)
        balance = float(customer.get("balance") or 0.0)
        available_credit = max(0.0, credit_limit - balance)

        return PortalCustomerProfile(
            id=customer["id"],
            name=customer["name"],
            group_name=customer.get("group_name") or "Wholesale",
            phone=customer.get("phone"),
            email=customer.get("email"),
            credit_limit=credit_limit,
            balance=balance,
            available_credit=available_credit,
            min_order_amount=float(customer.get("min_order_amount") or 0.0),
            order_cutoff_time=str(customer.get("order_cutoff_time")) if customer.get("order_cutoff_time") else None,
            allow_reorders=bool(customer.get("allow_reorders", True)),
            default_price_list_id=customer.get("default_price_list_id"),
            default_tax_rate_id=customer.get("default_tax_rate_id"),
            payment_term_id=customer.get("payment_term_id"),
            is_active=bool(customer.get("is_active", True)),
        )

    def get_categories(self, conn=None) -> List[PortalCatalogCategory]:
        """Fetch all product categories with product counts."""
        raw_cats = self.repo.get_categories(conn=conn)
        return [PortalCatalogCategory(**cat) for cat in raw_cats]
