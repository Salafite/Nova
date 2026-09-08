from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


# ============================================================
# Price List (T0083) & Price List Item (T0084) Models
# ============================================================

class PriceListCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    currency: str = 'USD'
    is_active: bool = True
    is_default: bool = False
    business_id: Optional[int] = None


class PriceListUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    business_id: Optional[int] = None


class PriceListResponse(AuditMixin):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    currency: str = 'USD'
    is_active: bool = True
    is_default: bool = False


class PriceListItemCreate(BaseModel):
    price_list_id: int
    product_id: int
    unit_price: float
    min_qty: Optional[float] = 1.0
    uom_id: Optional[int] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    line_number: int = 0
    business_id: Optional[int] = None


class PriceListItemUpdate(BaseModel):
    price_list_id: Optional[int] = None
    product_id: Optional[int] = None
    unit_price: Optional[float] = None
    min_qty: Optional[float] = None
    uom_id: Optional[int] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    line_number: Optional[int] = None
    business_id: Optional[int] = None


class PriceListItemResponse(AuditMixin):
    id: int
    price_list_id: int
    product_id: int
    unit_price: float
    min_qty: Optional[float] = None
    uom_id: Optional[int] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    line_number: int = 0


# ============================================================
# Volume Tier Break Models (T0116)
# ============================================================

class VolumeTierBreakCreate(BaseModel):
    price_list_id: Optional[int] = None
    product_id: Optional[int] = None
    min_quantity: float = 1.00
    max_quantity: Optional[float] = None
    unit_price: Optional[float] = None
    discount_percentage: float = 0.00
    discount_type: str = 'FixedPrice'  # FixedPrice | Percentage
    is_active: bool = True
    business_id: Optional[int] = None


class VolumeTierBreakUpdate(BaseModel):
    price_list_id: Optional[int] = None
    product_id: Optional[int] = None
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None
    unit_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    discount_type: Optional[str] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None


class VolumeTierBreakResponse(AuditMixin):
    id: int
    price_list_id: Optional[int] = None
    product_id: Optional[int] = None
    min_quantity: float = 1.00
    max_quantity: Optional[float] = None
    unit_price: Optional[float] = None
    discount_percentage: float = 0.00
    discount_type: str = 'FixedPrice'
    is_active: bool = True


# ============================================================
# Customer Group Price List Matrix Models (T0117)
# ============================================================

class CustomerGroupPriceListCreate(BaseModel):
    customer_group: str
    price_list_id: int
    priority: int = 0
    is_active: bool = True
    business_id: Optional[int] = None


class CustomerGroupPriceListUpdate(BaseModel):
    customer_group: Optional[str] = None
    price_list_id: Optional[int] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None


class CustomerGroupPriceListResponse(AuditMixin):
    id: int
    customer_group: str
    price_list_id: int
    priority: int = 0
    is_active: bool = True


# ============================================================
# Customer Contract & Special Price Models (T0118)
# ============================================================

class CustomerContractCreate(BaseModel):
    contract_number: Optional[str] = None
    customer_id: int
    product_id: int
    contracted_price: float
    discount_percentage: float = 0.00
    min_order_quantity: float = 1.00
    start_date: date
    end_date: Optional[date] = None
    status: str = 'Active'  # Draft | Active | Expired | Terminated
    is_active: bool = True
    business_id: Optional[int] = None


class CustomerContractUpdate(BaseModel):
    contract_number: Optional[str] = None
    customer_id: Optional[int] = None
    product_id: Optional[int] = None
    contracted_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    min_order_quantity: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None


class CustomerContractResponse(AuditMixin):
    id: int
    contract_number: str
    customer_id: int
    product_id: int
    contracted_price: float
    discount_percentage: float = 0.00
    min_order_quantity: float = 1.00
    start_date: date
    end_date: Optional[date] = None
    status: str = 'Active'
    is_active: bool = True


# ============================================================
# Promotional Rule / Buy-X-Get-Y Campaign Models (T0119)
# ============================================================

class PromotionalRuleCreate(BaseModel):
    code: Optional[str] = None
    name: str
    description: Optional[str] = None
    promo_type: str = 'BuyXGetY'  # BuyXGetY | PercentageDiscount | FixedDiscount
    buy_product_id: Optional[int] = None
    buy_quantity: float = 1.00
    get_product_id: Optional[int] = None
    get_quantity: float = 1.00
    get_discount_percentage: float = 100.00
    customer_group: Optional[str] = None
    customer_id: Optional[int] = None
    start_date: datetime
    end_date: datetime
    usage_limit: Optional[int] = None
    times_used: int = 0
    is_active: bool = True
    business_id: Optional[int] = None


class PromotionalRuleUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    promo_type: Optional[str] = None
    buy_product_id: Optional[int] = None
    buy_quantity: Optional[float] = None
    get_product_id: Optional[int] = None
    get_quantity: Optional[float] = None
    get_discount_percentage: Optional[float] = None
    customer_group: Optional[str] = None
    customer_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    usage_limit: Optional[int] = None
    times_used: Optional[int] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None


class PromotionalRuleResponse(AuditMixin):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    promo_type: str = 'BuyXGetY'
    buy_product_id: Optional[int] = None
    buy_quantity: float = 1.00
    get_product_id: Optional[int] = None
    get_quantity: float = 1.00
    get_discount_percentage: float = 100.00
    customer_group: Optional[str] = None
    customer_id: Optional[int] = None
    start_date: datetime
    end_date: datetime
    usage_limit: Optional[int] = None
    times_used: int = 0
    is_active: bool = True


# ============================================================
# Pricing Engine Calculation & Quote Models
# ============================================================

class PriceCalculateLineRequest(BaseModel):
    product_id: int
    quantity: float = Field(default=1.0, gt=0)
    unit_price: Optional[float] = Field(default=None, ge=0)
    uom_id: Optional[int] = None


class PriceCalculateRequest(BaseModel):
    customer_id: Optional[int] = None
    customer_group: Optional[str] = None
    price_list_id: Optional[int] = None
    lines: List[PriceCalculateLineRequest] = Field(default_factory=list)


class PriceCalculateLineResponse(BaseModel):
    product_id: int
    quantity: float
    base_unit_price: float
    final_unit_price: float
    discount_amount: float = 0.0
    discount_percentage: float = 0.0
    applied_source: str = 'DefaultPriceList'  # CustomerContract | CustomerGroup | VolumeTier | DefaultPriceList
    tier_applied: Optional[Dict[str, Any]] = None
    line_total: float


class PromotionalRewardItem(BaseModel):
    promo_id: int
    promo_code: str
    promo_name: str
    buy_product_id: int
    reward_product_id: int
    reward_quantity: float
    reward_discount_percentage: float = 100.00
    notes: str = ''


class PriceCalculateResponse(BaseModel):
    customer_id: Optional[int] = None
    customer_group: Optional[str] = None
    resolved_price_list_id: Optional[int] = None
    lines: List[PriceCalculateLineResponse] = Field(default_factory=list)
    promotional_rewards: List[PromotionalRewardItem] = Field(default_factory=list)
    subtotal: float = 0.0
    total_discount: float = 0.0
    final_total: float = 0.0
