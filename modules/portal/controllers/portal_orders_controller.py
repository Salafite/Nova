import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from modules.portal.services.portal_pricing_service import PortalPricingService
from modules.portal.services.portal_order_service import PortalOrderService
from modules.portal.models.portal import (
    PortalCatalogResponse,
    PortalCatalogQuery,
    PortalAccountSummary,
    PortalOrderCreate,
    PortalOrderResponse,
    PortalReorderRequest,
    PortalOrderCancelRequest,
    OrderValidationResponse,
    CutoffValidationResponse,
    PortalOrderLineCreate,
)
from packages.auth.deps import get_current_portal_customer, require_portal_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portal", tags=["Customer Portal"])


def get_pricing_service() -> PortalPricingService:
    return PortalPricingService()


def get_order_service() -> PortalOrderService:
    return PortalOrderService()


# ----------------------------------------------------------------------
# Customer Portal Catalog & Contracted Pricing Endpoints
# ----------------------------------------------------------------------

@router.get("/catalog", response_model=PortalCatalogResponse)
def get_portal_catalog(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    search: Optional[str] = Query(None, description="Search product name or SKU"),
    in_stock_only: bool = Query(False, description="Filter in-stock items only"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    current_customer: dict = Depends(get_current_portal_customer),
    pricing_svc: PortalPricingService = Depends(get_pricing_service),
):
    """Retrieve product catalog with customer's contracted pricing, categories, and stock availability."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )

    query = PortalCatalogQuery(
        category_id=category_id,
        search=search,
        in_stock_only=in_stock_only,
        page=page,
        limit=limit,
    )
    try:
        return pricing_svc.get_catalog(customer_id=customer_id, query=query)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch portal catalog for customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# ----------------------------------------------------------------------
# Customer Account Overview & Cutoff Verification Endpoints
# ----------------------------------------------------------------------

@router.get("/account/summary", response_model=PortalAccountSummary)
def get_portal_account_summary(
    current_customer: dict = Depends(get_current_portal_customer),
    pricing_svc: PortalPricingService = Depends(get_pricing_service),
):
    """Retrieve authenticated customer account metrics, balance, credit limit, and ordering configuration."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )

    try:
        return pricing_svc.get_account_summary(customer_id=customer_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch account summary for customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/cutoff-status", response_model=CutoffValidationResponse)
def get_portal_cutoff_status(
    current_customer: dict = Depends(get_current_portal_customer),
    order_svc: PortalOrderService = Depends(get_order_service),
):
    """Check ordering cutoff status and calculated next delivery date for authenticated customer."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )

    try:
        return order_svc.validate_cutoff_time(customer_id=customer_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to check cutoff status for customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# ----------------------------------------------------------------------
# Replenishment Order Validation & Placement Endpoints
# ----------------------------------------------------------------------

@router.post("/orders/validate", response_model=OrderValidationResponse)
def validate_portal_order(
    items: List[PortalOrderLineCreate],
    current_customer: dict = Depends(get_current_portal_customer),
    order_svc: PortalOrderService = Depends(get_order_service),
):
    """Validate replenishment cart items against minimum order amount, contracted pricing, and cutoff times."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )

    try:
        return order_svc.validate_order(customer_id=customer_id, items=items)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to validate order for customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/orders", response_model=PortalOrderResponse, status_code=status.HTTP_201_CREATED)
def create_portal_order(
    order_in: PortalOrderCreate,
    current_customer: dict = Depends(require_portal_permission("PORTAL_ORDER")),
    order_svc: PortalOrderService = Depends(get_order_service),
):
    """Submit a new replenishment sales order with contracted pricing and delivery date scheduling."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )
    user_id = current_customer.get("id")

    try:
        return order_svc.create_order(customer_id=customer_id, order_in=order_in, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create order for customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/orders")
def list_portal_orders(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by order status (Draft, Confirmed, Shipped, Delivered, Cancelled)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_customer: dict = Depends(get_current_portal_customer),
    order_svc: PortalOrderService = Depends(get_order_service),
):
    """List customer order history with itemized line summaries strictly isolated to customer account."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )

    try:
        orders, total = order_svc.get_orders(
            customer_id=customer_id,
            status=status_filter,
            page=page,
            limit=limit,
        )
        return {
            "items": orders,
            "total": total,
            "page": page,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Failed to list orders for customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/orders/{id}", response_model=PortalOrderResponse)
def get_portal_order_detail(
    id: int,
    current_customer: dict = Depends(get_current_portal_customer),
    order_svc: PortalOrderService = Depends(get_order_service),
):
    """Retrieve detailed order information with full line breakdown, scoped strictly to customer."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )

    try:
        order = order_svc.get_order_by_id(customer_id=customer_id, order_id=id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order #{id} not found")
        return order
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch order #{id} for customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/orders/{id}/reorder", response_model=PortalOrderResponse, status_code=status.HTTP_201_CREATED)
def reorder_portal_order(
    id: int,
    body: Optional[PortalReorderRequest] = None,
    current_customer: dict = Depends(require_portal_permission("PORTAL_ORDER")),
    order_svc: PortalOrderService = Depends(get_order_service),
):
    """1-Click Replenishment Reorder from previous order, recalculating prices with contracted pricing."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )
    user_id = current_customer.get("id")

    req = body or PortalReorderRequest()
    req.order_id = id

    try:
        return order_svc.reorder(customer_id=customer_id, reorder_in=req, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to reorder #{id} for customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/orders/{id}/cancel", response_model=PortalOrderResponse)
def cancel_portal_order(
    id: int,
    body: Optional[PortalOrderCancelRequest] = None,
    current_customer: dict = Depends(require_portal_permission("PORTAL_ORDER")),
    order_svc: PortalOrderService = Depends(get_order_service),
):
    """Cancel an unfulfilled replenishment order placed by the authenticated customer."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )
    user_id = current_customer.get("id")

    try:
        return order_svc.cancel_order(customer_id=customer_id, order_id=id, cancel_in=body, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to cancel order #{id} for customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
