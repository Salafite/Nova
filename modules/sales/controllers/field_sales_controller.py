import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from packages.auth.deps import require_permission, get_current_user
from modules.sales.models.field_sales import (
    CustomerOrderSummary,
    FieldSalesBatchSyncRequest,
    FieldSalesBatchSyncResponse,
    FieldSalesCatalogBundle,
    FieldSalesCustomerProfile,
    FieldSalesResolveConflictRequest,
    FieldSalesValidationRequest,
    FieldSalesValidationResponse,
    OrderSyncResult,
)
from modules.sales.services.field_sales_catalog_service import (
    FieldSalesCatalogService,
    field_sales_catalog_service as default_catalog_service,
)
from modules.sales.services.field_sales_sync_service import (
    FieldSalesSyncService,
    field_sales_sync_service as default_sync_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/sales/mobile",
    tags=["Field Sales Mobile"],
    dependencies=[Depends(require_permission("FIELD_SALES_MOBILE"))],
)

v1_router = APIRouter(
    prefix="/api/v1/sales/field",
    tags=["Field Sales Mobile"],
    dependencies=[Depends(require_permission("FIELD_SALES_MOBILE"))],
)

_catalog_svc: FieldSalesCatalogService = default_catalog_service
_sync_svc: FieldSalesSyncService = default_sync_service


# ---------------------------------------------------------------------------
# 1. Mobile Catalog Delta & Full Export
# ---------------------------------------------------------------------------

@router.get(
    "/catalog",
    response_model=FieldSalesCatalogBundle,
    summary="Get mobile catalog bundle",
    description="Retrieve product catalog with warehouse stock levels, barcodes, customer profiles with payment terms, and contracted price lists for offline caching.",
)
def get_mobile_catalog(
    delta_timestamp: Optional[str] = Query(
        None,
        description="ISO timestamp of last sync for delta export (e.g. 2026-08-20T10:00:00Z)",
    ),
    warehouse_id: Optional[int] = Query(
        None,
        description="Filter products and stock levels by warehouse ID",
    ),
    sales_rep_id: Optional[int] = Query(
        None,
        description="Filter customer assignments by sales representative user ID",
    ),
) -> FieldSalesCatalogBundle:
    """Fetch complete or delta catalog bundle optimized for field sales offline operations."""
    try:
        bundle = _catalog_svc.get_mobile_catalog(
            delta_timestamp=delta_timestamp,
            warehouse_id=warehouse_id,
            sales_rep_id=sales_rep_id,
        )
        return bundle
    except Exception as e:
        logger.error(f"Error fetching field sales mobile catalog: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch mobile catalog bundle: {str(e)}",
        ) from e


# ---------------------------------------------------------------------------
# 2. Customer Profiles with Credit Limits & Order History
# ---------------------------------------------------------------------------

@router.get(
    "/customers",
    response_model=List[FieldSalesCustomerProfile],
    summary="Get customer profiles for mobile sales",
    description="Retrieve customer profiles with credit limits, balances, payment terms, and recent 5 order summaries for quick field reordering.",
)
def get_mobile_customers(
    delta_timestamp: Optional[str] = Query(
        None,
        description="ISO timestamp of last sync for customer delta updates",
    ),
    sales_rep_id: Optional[int] = Query(
        None,
        description="Filter customers assigned to a specific sales rep",
    ),
    include_recent_orders: bool = Query(
        True,
        description="Whether to include recent orders and line item summaries",
    ),
) -> List[FieldSalesCustomerProfile]:
    """Fetch customer list with financial terms and recent orders."""
    try:
        customers = _catalog_svc.get_customers(
            delta_timestamp=delta_timestamp,
            sales_rep_id=sales_rep_id,
            include_recent_orders=include_recent_orders,
        )
        return customers
    except Exception as e:
        logger.error(f"Error fetching field sales customers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch customer profiles: {str(e)}",
        ) from e


# ---------------------------------------------------------------------------
# 3. Customer Order History Breakdown
# ---------------------------------------------------------------------------

@router.get(
    "/customers/{customer_id}/history",
    response_model=List[CustomerOrderSummary],
    summary="Get customer order history",
    description="Fetch recent sales orders and line items for a specific customer for 1-tap reordering in the field.",
)
def get_customer_history(
    customer_id: int,
    limit: int = Query(
        5,
        ge=1,
        le=50,
        description="Maximum number of historical orders to retrieve",
    ),
) -> List[CustomerOrderSummary]:
    """Fetch order history for a single customer."""
    try:
        history = _catalog_svc.get_customer_history(
            customer_id=customer_id,
            limit=limit,
        )
        return history
    except Exception as e:
        logger.error(
            f"Error fetching order history for customer {customer_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch customer order history: {str(e)}",
        ) from e


# ---------------------------------------------------------------------------
# 4. Batch Order Sync (Idempotent with Atomic Transaction Isolation)
# ---------------------------------------------------------------------------

@router.post(
    "/sync",
    response_model=FieldSalesBatchSyncResponse,
    summary="Sync offline sales orders batch",
    description="Process queued offline orders atomically. Verifies idempotency via client_order_uuid to prevent duplicate insertion, validates stock availability, deducts inventory, and returns structured sync results.",
)
def sync_offline_orders(
    request: FieldSalesBatchSyncRequest,
    current_user: dict = Depends(get_current_user),
) -> FieldSalesBatchSyncResponse:
    """Synchronize offline sales orders batch."""
    try:
        # If order doesn't have sales_rep_id explicitly, attribute it to the authenticated user
        user_id = current_user.get("id")
        if user_id:
            for order in request.orders:
                if not order.sales_rep_id:
                    order.sales_rep_id = user_id

        result = _sync_svc.sync_batch(request)
        return result
    except Exception as e:
        logger.error(f"Error processing offline batch sync: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to synchronize offline orders: {str(e)}",
        ) from e


# ---------------------------------------------------------------------------
# 5. Pre-Sync Conflict Validation (Dry-Run)
# ---------------------------------------------------------------------------

@router.post(
    "/validate",
    response_model=FieldSalesValidationResponse,
    summary="Pre-sync order conflict validation",
    description="Perform dry-run validation against live database state to detect out-of-stock, insufficient quantity, price mismatch, or credit limit exceeded before committing.",
)
def validate_offline_orders(
    request: FieldSalesValidationRequest,
) -> FieldSalesValidationResponse:
    """Validate offline orders without modifying database state."""
    try:
        validation_result = _sync_svc.validate_batch(request)
        return validation_result
    except Exception as e:
        logger.error(f"Error validating offline orders: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate offline orders: {str(e)}",
        ) from e


# ---------------------------------------------------------------------------
# 6. Conflict Resolution & Direct Sync
# ---------------------------------------------------------------------------

@router.post(
    "/resolve-conflict",
    response_model=OrderSyncResult,
    summary="Resolve conflict and sync order",
    description="Apply sales rep conflict resolution actions (adjust_qty, substitute, accept_price, remove_item, backorder) and commit order synchronization.",
)
def resolve_conflict_and_sync(
    request: FieldSalesResolveConflictRequest,
    current_user: dict = Depends(get_current_user),
) -> OrderSyncResult:
    """Apply resolutions and commit order synchronization."""
    try:
        user_id = current_user.get("id")
        if user_id and not request.order_data.sales_rep_id:
            request.order_data.sales_rep_id = user_id

        result = _sync_svc.resolve_and_sync(request)
        return result
    except Exception as e:
        logger.error(
            f"Error resolving conflict for order {request.client_order_uuid}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve order conflict: {str(e)}",
        ) from e


@router.post(
    "/resolve",
    response_model=OrderSyncResult,
    include_in_schema=False,
)
def resolve_conflict_alias(
    request: FieldSalesResolveConflictRequest,
    current_user: dict = Depends(get_current_user),
) -> OrderSyncResult:
    """Alias for /resolve-conflict endpoint."""
    return resolve_conflict_and_sync(request, current_user=current_user)


# ---------------------------------------------------------------------------
# Route definitions for v1_router (/api/v1/sales/field/*)
# ---------------------------------------------------------------------------

@v1_router.get("/catalog", response_model=FieldSalesCatalogBundle, summary="Get mobile catalog bundle (v1)")
def get_mobile_catalog_v1(
    delta_timestamp: Optional[str] = Query(None),
    warehouse_id: Optional[int] = Query(None),
    sales_rep_id: Optional[int] = Query(None),
) -> FieldSalesCatalogBundle:
    return get_mobile_catalog(delta_timestamp=delta_timestamp, warehouse_id=warehouse_id, sales_rep_id=sales_rep_id)


@v1_router.get("/customers", response_model=List[FieldSalesCustomerProfile], summary="Get customer profiles (v1)")
def get_mobile_customers_v1(
    delta_timestamp: Optional[str] = Query(None),
    sales_rep_id: Optional[int] = Query(None),
    include_recent_orders: bool = Query(True),
) -> List[FieldSalesCustomerProfile]:
    return get_mobile_customers(delta_timestamp=delta_timestamp, sales_rep_id=sales_rep_id, include_recent_orders=include_recent_orders)


@v1_router.get("/customers/{customer_id}/history", response_model=List[CustomerOrderSummary], summary="Get customer order history (v1)")
def get_customer_history_v1(
    customer_id: int,
    limit: int = Query(5, ge=1, le=50),
) -> List[CustomerOrderSummary]:
    return get_customer_history(customer_id=customer_id, limit=limit)


@v1_router.post("/sync", response_model=FieldSalesBatchSyncResponse, summary="Sync offline sales orders batch (v1)")
def sync_offline_orders_v1(
    request: FieldSalesBatchSyncRequest,
    current_user: dict = Depends(get_current_user),
) -> FieldSalesBatchSyncResponse:
    return sync_offline_orders(request=request, current_user=current_user)


@v1_router.post("/validate", response_model=FieldSalesValidationResponse, summary="Pre-sync order conflict validation (v1)")
def validate_offline_orders_v1(
    request: FieldSalesValidationRequest,
) -> FieldSalesValidationResponse:
    return validate_offline_orders(request=request)


@v1_router.post("/resolve-conflict", response_model=OrderSyncResult, summary="Resolve conflict and sync order (v1)")
def resolve_conflict_and_sync_v1(
    request: FieldSalesResolveConflictRequest,
    current_user: dict = Depends(get_current_user),
) -> OrderSyncResult:
    return resolve_conflict_and_sync(request=request, current_user=current_user)


@v1_router.post("/resolve", response_model=OrderSyncResult, include_in_schema=False)
def resolve_conflict_alias_v1(
    request: FieldSalesResolveConflictRequest,
    current_user: dict = Depends(get_current_user),
) -> OrderSyncResult:
    return resolve_conflict_and_sync(request=request, current_user=current_user)


