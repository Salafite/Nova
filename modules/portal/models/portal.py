from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field
from modules.core.models.base import AuditMixin


# ----------------------------------------------------------------------
# Customer Portal Profile & Account Summary Models
# ----------------------------------------------------------------------

class PortalCustomerProfile(BaseModel):
    """Customer profile and B2B portal configuration."""
    id: int
    name: str
    group_name: str = 'Wholesale'
    phone: Optional[str] = None
    email: Optional[str] = None
    credit_limit: float = 0.0
    balance: float = 0.0
    available_credit: float = 0.0
    min_order_amount: float = 0.0
    order_cutoff_time: Optional[str] = None
    allow_reorders: bool = True
    default_price_list_id: Optional[int] = None
    default_tax_rate_id: Optional[int] = None
    payment_term_id: Optional[int] = None
    is_active: bool = True


class PortalAccountSummary(BaseModel):
    """Dashboard account summary for authenticated B2B customer."""
    customer_id: int
    customer_name: str
    group_name: str = 'Wholesale'
    email: Optional[str] = None
    phone: Optional[str] = None
    credit_limit: float = 0.0
    current_balance: float = 0.0
    available_credit: float = 0.0
    min_order_amount: float = 0.0
    order_cutoff_time: Optional[str] = None
    allow_reorders: bool = True
    open_invoices_count: int = 0
    total_unpaid_amount: float = 0.0
    recent_orders_count: int = 0
    default_price_list_id: Optional[int] = None
    default_price_list_name: Optional[str] = None


# ----------------------------------------------------------------------
# B2B Catalog & Contracted Pricing Models
# ----------------------------------------------------------------------

class PortalCatalogItem(BaseModel):
    """Product catalog item with customer-specific contracted pricing and stock availability."""
    id: int
    product_code: str
    product_name: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    uom_id: Optional[int] = None
    uom_name: Optional[str] = None
    base_price: float = 0.0
    contracted_price: float = 0.0
    is_contracted: bool = False
    discount_percent: float = 0.0
    stock_qty: float = 0.0
    is_in_stock: bool = True
    image_url: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class PortalCatalogCategory(BaseModel):
    """Category filter item for portal catalog."""
    id: int
    category_name: str
    item_count: int = 0


class PortalCatalogQuery(BaseModel):
    """Query parameters for portal catalog search and filter."""
    category_id: Optional[int] = None
    search: Optional[str] = None
    in_stock_only: bool = False
    page: int = 1
    limit: int = 50


class PortalCatalogResponse(BaseModel):
    """Paginated catalog response with customer portal settings."""
    items: List[PortalCatalogItem]
    total: int
    page: int
    limit: int
    categories: List[PortalCatalogCategory] = []
    min_order_amount: float = 0.0
    order_cutoff_time: Optional[str] = None


# ----------------------------------------------------------------------
# Cutoff Time & Minimum Order Validation Models
# ----------------------------------------------------------------------

class CutoffValidationResponse(BaseModel):
    """Result of order cutoff time check for delivery scheduling."""
    is_past_cutoff: bool
    cutoff_time: Optional[str] = None
    current_time: str
    current_timezone: str = "UTC"
    next_delivery_date: date
    message: str


class OrderValidationResponse(BaseModel):
    """Validation response checking minimum order amount and order cutoff times."""
    is_valid: bool
    subtotal: float
    min_order_amount: float
    meets_minimum: bool
    cutoff_status: CutoffValidationResponse
    errors: List[str] = []
    warnings: List[str] = []


# ----------------------------------------------------------------------
# Order Creation, Line Items & Management Models
# ----------------------------------------------------------------------

class PortalOrderLineCreate(BaseModel):
    """Line item input when placing an order from the portal."""
    model_config = ConfigDict(extra='forbid')

    product_id: int
    qty: float = Field(..., gt=0)
    notes: Optional[str] = None


class PortalOrderCreate(BaseModel):
    """Order placement payload from authenticated customer."""
    model_config = ConfigDict(extra='forbid')

    items: List[PortalOrderLineCreate] = Field(..., min_length=1)
    warehouse_id: Optional[int] = None
    requested_delivery_date: Optional[date] = None
    notes: Optional[str] = None
    status: str = 'Confirmed'  # 'Draft' or 'Confirmed'


class PortalOrderLineResponse(BaseModel):
    """Order line item detail in portal order view."""
    id: Optional[int] = None
    sales_order_id: Optional[int] = None
    product_id: Optional[int] = None
    product_code: Optional[str] = None
    product_name: str
    uom_name: Optional[str] = None
    qty: float
    unit_price: float
    line_total: float
    line_number: int = 0


class PortalOrderResponse(AuditMixin):
    """Order header and line items response in portal."""
    id: int
    order_number: str
    customer_id: int
    customer_name: Optional[str] = None
    warehouse_id: Optional[int] = None
    subtotal: float
    tax: float
    grand_total: float
    status: str
    order_date: date
    requested_delivery_date: Optional[date] = None
    notes: Optional[str] = None
    lines: List[PortalOrderLineResponse] = []


class PortalReorderRequest(BaseModel):
    """Request to create a duplicate replenishment order from history."""
    model_config = ConfigDict(extra='forbid')

    order_id: Optional[int] = None
    requested_delivery_date: Optional[date] = None
    notes: Optional[str] = None
    status: str = 'Confirmed'


class PortalOrderCancelRequest(BaseModel):
    """Request to cancel an unfulfilled portal order."""
    model_config = ConfigDict(extra='forbid')

    reason: Optional[str] = None


# ----------------------------------------------------------------------
# Invoice Settlement & Stripe Checkout Models
# ----------------------------------------------------------------------

class PortalInvoiceResponse(AuditMixin):
    """Customer invoice view for portal."""
    id: int
    invoice_number: str
    invoice_type: str = 'Sales'
    partner_id: int
    customer_name: Optional[str] = None
    sales_order_id: Optional[int] = None
    sales_order_number: Optional[str] = None
    issue_date: date
    due_date: date
    total_amount: float
    paid_amount: float = 0.0
    balance_due: float = 0.0
    status: str  # 'Unpaid', 'Partially Paid', 'Paid', 'Cancelled'
    stripe_payment_intent_id: Optional[str] = None
    stripe_checkout_session_id: Optional[str] = None
    payment_link: Optional[str] = None
    notes: Optional[str] = None


class InvoiceCheckoutSessionRequest(BaseModel):
    """Request to create a Stripe Checkout session for a specific invoice."""
    model_config = ConfigDict(extra='forbid')

    invoice_id: int
    payment_method_types: List[str] = Field(default_factory=lambda: ["card", "us_bank_account"])
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class BalanceSettlementCheckoutRequest(BaseModel):
    """Request to create a Stripe Checkout session to settle outstanding account balance."""
    model_config = ConfigDict(extra='forbid')

    amount: float = Field(..., gt=0)
    invoice_ids: Optional[List[int]] = None
    payment_method_types: List[str] = Field(default_factory=lambda: ["card", "us_bank_account"])
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PortalCheckoutSessionResponse(BaseModel):
    """Response returned upon creating a hosted Stripe Checkout session."""
    session_id: str
    checkout_url: str
    customer_id: int
    amount: float
    amount_cents: int
    currency: str = "usd"
    settlement_type: str = "invoice"  # "invoice" or "balance"
    invoice_id: Optional[int] = None
    payment_method_types: List[str] = ["card", "us_bank_account"]
    status: str = "open"


class PaymentSessionStatusResponse(BaseModel):
    """Payment verification and status response from Stripe session."""
    session_id: str
    status: str  # 'open', 'complete', 'expired'
    payment_status: str  # 'paid', 'unpaid', 'no_payment_required'
    payment_intent_id: Optional[str] = None
    amount_total: Optional[float] = None
    currency: Optional[str] = "usd"
    customer_id: Optional[int] = None
    invoice_id: Optional[int] = None
    customer_email: Optional[str] = None
