from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def _get_utc_now() -> datetime:
    return datetime.now(timezone.utc)



class ConflictType(str, Enum):
    OUT_OF_STOCK = "OUT_OF_STOCK"
    INSUFFICIENT_QTY = "INSUFFICIENT_QTY"
    PRICE_MISMATCH = "PRICE_MISMATCH"
    CUSTOMER_INACTIVE = "CUSTOMER_INACTIVE"
    CREDIT_LIMIT_EXCEEDED = "CREDIT_LIMIT_EXCEEDED"


class SyncStatus(str, Enum):
    SYNCED = "Synced"
    PENDING = "Pending"
    CONFLICT = "Conflict"
    FAILED = "Failed"


class ResolutionAction(str, Enum):
    ADJUST_QTY = "adjust_qty"
    BACKORDER = "backorder"
    SUBSTITUTE = "substitute"
    REMOVE_ITEM = "remove_item"
    ACCEPT_PRICE = "accept_price"


# ---------------------------------------------------------------------------
# Catalog & Pricing Models
# ---------------------------------------------------------------------------

class CatalogProductItem(BaseModel):
    id: int
    sku: Optional[str] = None
    barcode: Optional[str] = None
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    category_id: Optional[int] = None
    uom_id: Optional[int] = None
    uom_code: Optional[str] = None
    base_price: float = 0.0
    cost_price: Optional[float] = None
    available_qty: float = 0.0
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    warehouse_stock: Dict[str, float] = Field(default_factory=dict)
    is_active: bool = True
    image_url: Optional[str] = None
    tax_rate_id: Optional[int] = None
    tax_rate: Optional[float] = None
    updated_at: Optional[datetime] = None


class CustomerPriceRule(BaseModel):
    id: Optional[int] = None
    price_list_id: int
    product_id: int
    unit_price: float
    min_qty: Optional[float] = 1.0
    uom_id: Optional[int] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


# ---------------------------------------------------------------------------
# Customer Profiles & History Models
# ---------------------------------------------------------------------------

class CustomerOrderLineSummary(BaseModel):
    product_id: Optional[int] = None
    product_name: str
    qty: float
    unit_price: float
    line_total: float


class CustomerOrderSummary(BaseModel):
    id: int
    order_number: str
    order_date: Optional[date] = None
    grand_total: float
    status: str
    item_count: int = 0
    lines: List[CustomerOrderLineSummary] = Field(default_factory=list)


class FieldSalesCustomerProfile(BaseModel):
    id: int
    name: str
    group_name: Optional[str] = "Retail"
    phone: Optional[str] = None
    email: Optional[str] = None
    credit_limit: float = 0.0
    balance: float = 0.0
    available_credit: float = 0.0
    payment_term_id: Optional[int] = None
    payment_term_name: Optional[str] = None
    payment_term_days: Optional[int] = None
    default_price_list_id: Optional[int] = None
    default_tax_rate_id: Optional[int] = None
    tax_rate_pct: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    is_active: bool = True
    recent_orders: List[CustomerOrderSummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Mobile Catalog Export Bundle
# ---------------------------------------------------------------------------

class FieldSalesCatalogBundle(BaseModel):
    sync_timestamp: datetime = Field(default_factory=_get_utc_now)
    delta_timestamp: Optional[datetime] = None
    products: List[CatalogProductItem] = Field(default_factory=list)
    customers: List[FieldSalesCustomerProfile] = Field(default_factory=list)
    price_rules: List[CustomerPriceRule] = Field(default_factory=list)
    warehouses: List[Dict[str, Any]] = Field(default_factory=list)
    tax_rates: List[Dict[str, Any]] = Field(default_factory=list)
    payment_terms: List[Dict[str, Any]] = Field(default_factory=list)
    total_products: int = 0
    total_customers: int = 0


# ---------------------------------------------------------------------------
# Offline Order Submission Models
# ---------------------------------------------------------------------------

class FieldSalesOrderLine(BaseModel):
    line_number: int = 1
    product_id: int
    product_name: str
    sku: Optional[str] = None
    qty: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    discount_pct: Optional[float] = 0.0
    line_total: float = Field(0.0, ge=0)
    uom_id: Optional[int] = None
    notes: Optional[str] = None


class FieldSalesOrderSubmission(BaseModel):
    client_order_uuid: str = Field(..., min_length=1, max_length=64)
    order_number: Optional[str] = None
    customer_id: int
    warehouse_id: Optional[int] = None
    sales_rep_id: Optional[int] = None
    order_date: Optional[date] = None
    offline_created_at: Optional[datetime] = None
    subtotal: float = 0.0
    tax: float = 0.0
    grand_total: float = 0.0
    price_list_id: Optional[int] = None
    tax_rate_id: Optional[int] = None
    payment_term_id: Optional[int] = None
    notes: Optional[str] = None
    signature: Optional[str] = None
    lines: List[FieldSalesOrderLine] = Field(..., min_length=1)


class FieldSalesBatchSyncRequest(BaseModel):
    orders: List[FieldSalesOrderSubmission]
    device_id: Optional[str] = None
    client_timestamp: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Stock Conflict Breakdown & Reporting Models
# ---------------------------------------------------------------------------

class LineConflictDetail(BaseModel):
    line_number: int
    product_id: int
    product_name: str
    conflict_type: str  # ConflictType value: 'OUT_OF_STOCK', 'INSUFFICIENT_QTY', 'PRICE_MISMATCH', etc.
    requested_qty: float
    available_qty: float
    requested_price: Optional[float] = None
    current_price: Optional[float] = None
    message: str
    suggested_action: Optional[str] = None  # 'adjust_qty', 'backorder', 'substitute', etc.
    suggested_substitutes: Optional[List[Dict[str, Any]]] = None


class OrderSyncResult(BaseModel):
    client_order_uuid: str
    server_order_id: Optional[int] = None
    order_number: Optional[str] = None
    status: str  # 'Synced', 'Conflict', 'Failed', 'AlreadySynced'
    is_duplicate: bool = False
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    grand_total: Optional[float] = None
    conflicts: List[LineConflictDetail] = Field(default_factory=list)
    message: Optional[str] = None


class FieldSalesBatchSyncResponse(BaseModel):
    success: bool
    synced_count: int = 0
    conflict_count: int = 0
    failed_count: int = 0
    results: List[OrderSyncResult] = Field(default_factory=list)
    sync_timestamp: datetime = Field(default_factory=_get_utc_now)
    message: Optional[str] = None


class FieldSalesValidationRequest(BaseModel):
    orders: List[FieldSalesOrderSubmission]


class FieldSalesValidationResponse(BaseModel):
    valid: bool
    total_orders: int = 0
    conflicts_found: int = 0
    results: List[OrderSyncResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Conflict Resolution Request
# ---------------------------------------------------------------------------

class ConflictResolutionItem(BaseModel):
    line_number: int
    product_id: int
    action: str  # 'adjust_qty', 'backorder', 'substitute', 'remove_item', 'accept_price'
    adjusted_qty: Optional[float] = None
    substitute_product_id: Optional[int] = None
    substitute_product_name: Optional[str] = None
    accepted_price: Optional[float] = None


class FieldSalesResolveConflictRequest(BaseModel):
    client_order_uuid: str
    order_data: FieldSalesOrderSubmission
    resolutions: List[ConflictResolutionItem] = Field(default_factory=list)
