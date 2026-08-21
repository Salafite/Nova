from typing import Optional, Any, List
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class TierRule(BaseModel):
    min_margin_pct: float = Field(0.0, ge=0)
    max_margin_pct: Optional[float] = None
    commission_rate: float = Field(..., ge=0, le=100)


# ---------------------------------------------------------------------------
# Commission Rules (Nova.t0107)
# ---------------------------------------------------------------------------

class CommissionRuleCreate(BaseModel):
    rule_name: str = Field(..., max_length=100)
    sales_rep_id: Optional[int] = None
    base_commission_rate: float = Field(5.00, ge=0, le=100)
    min_margin_threshold: float = Field(15.00, ge=0, le=100)
    tier_rules: List[dict] = Field(default_factory=list)
    discount_penalty_rate: float = Field(0.50, ge=0)
    is_active: bool = True
    notes: Optional[str] = None


class CommissionRuleUpdate(BaseModel):
    rule_name: Optional[str] = Field(None, max_length=100)
    sales_rep_id: Optional[int] = None
    base_commission_rate: Optional[float] = Field(None, ge=0, le=100)
    min_margin_threshold: Optional[float] = Field(None, ge=0, le=100)
    tier_rules: Optional[List[dict]] = None
    discount_penalty_rate: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class CommissionRuleResponse(AuditMixin):
    id: int
    rule_name: str
    sales_rep_id: Optional[int] = None
    sales_rep_name: Optional[str] = None
    base_commission_rate: float
    min_margin_threshold: float
    tier_rules: List[dict] = Field(default_factory=list)
    discount_penalty_rate: float
    is_active: bool
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Commission Payouts & Ledger (Nova.t0108)
# ---------------------------------------------------------------------------

class CommissionPayoutCreate(BaseModel):
    payout_number: Optional[str] = Field(None, max_length=50)
    sales_rep_id: int
    invoice_id: Optional[int] = None
    payment_id: Optional[int] = None
    rule_id: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    collected_amount: float = Field(0.0, ge=0)
    realized_gross_margin: float = 0.0
    commission_rate: float = Field(0.0, ge=0, le=100)
    commission_amount: float = Field(0.0, ge=0)
    discount_penalty: float = Field(0.0, ge=0)
    net_commission_amount: float = 0.0
    status: str = 'Pending'
    payment_date: Optional[date] = None
    notes: Optional[str] = None


class CommissionPayoutUpdate(BaseModel):
    payout_number: Optional[str] = Field(None, max_length=50)
    sales_rep_id: Optional[int] = None
    invoice_id: Optional[int] = None
    payment_id: Optional[int] = None
    rule_id: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    collected_amount: Optional[float] = Field(None, ge=0)
    realized_gross_margin: Optional[float] = None
    commission_rate: Optional[float] = Field(None, ge=0, le=100)
    commission_amount: Optional[float] = Field(None, ge=0)
    discount_penalty: Optional[float] = Field(None, ge=0)
    net_commission_amount: Optional[float] = None
    status: Optional[str] = None
    payment_date: Optional[date] = None
    notes: Optional[str] = None


class CommissionPayoutResponse(AuditMixin):
    id: int
    payout_number: str
    sales_rep_id: int
    sales_rep_name: Optional[str] = None
    invoice_id: Optional[int] = None
    invoice_number: Optional[str] = None
    payment_id: Optional[int] = None
    rule_id: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    collected_amount: float
    realized_gross_margin: float
    commission_rate: float
    commission_amount: float
    discount_penalty: float
    net_commission_amount: float
    status: str
    payment_date: Optional[date] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Commission Calculation & Statement Schemas
# ---------------------------------------------------------------------------

class CommissionCalculationRequest(BaseModel):
    sales_rep_id: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    rule_id: Optional[int] = None
    include_pending: bool = True


class CommissionStatementItem(BaseModel):
    invoice_id: Optional[int] = None
    invoice_number: Optional[str] = None
    order_number: Optional[str] = None
    payment_id: Optional[int] = None
    payment_date: Optional[date] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    invoice_total: float = 0.0
    collected_cash: float = 0.0
    cogs: float = 0.0
    freight_cost: float = 0.0
    discount_amount: float = 0.0
    realized_gross_margin: float = 0.0
    realized_margin_pct: float = 0.0
    commission_rate: float = 0.0
    gross_commission: float = 0.0
    discount_penalty: float = 0.0
    net_commission: float = 0.0
    status: str = 'Pending'


class CommissionStatementResponse(BaseModel):
    sales_rep_id: int
    sales_rep_name: Optional[str] = None
    sales_rep_email: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    rule_name: Optional[str] = None
    total_booked_sales: float = 0.0
    total_collected_amount: float = 0.0
    total_cogs: float = 0.0
    total_freight_cost: float = 0.0
    total_discounts_granted: float = 0.0
    total_realized_gross_margin: float = 0.0
    average_realized_margin_pct: float = 0.0
    gross_commission_earned: float = 0.0
    total_discount_penalties: float = 0.0
    net_commission_payable: float = 0.0
    paid_commission_amount: float = 0.0
    pending_commission_amount: float = 0.0
    items: List[CommissionStatementItem] = Field(default_factory=list)


class CommissionSummaryItem(BaseModel):
    sales_rep_id: int
    sales_rep_name: str
    sales_rep_email: Optional[str] = None
    total_invoices: int = 0
    total_collected: float = 0.0
    total_gross_margin: float = 0.0
    avg_margin_pct: float = 0.0
    gross_commission: float = 0.0
    discount_penalty: float = 0.0
    net_commission: float = 0.0
    paid_commission: float = 0.0
    pending_commission: float = 0.0
