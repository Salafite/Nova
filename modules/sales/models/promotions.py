from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class PromotionCreate(BaseModel):
    code: Optional[str] = None
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    promo_type: str = 'BuyXGetY'
    buy_product_id: Optional[int] = None
    buy_quantity: float = Field(1.0, ge=0)
    get_product_id: Optional[int] = None
    get_quantity: float = Field(1.0, ge=0)
    get_discount_percentage: float = Field(100.0, ge=0, le=100)
    customer_group: Optional[str] = None
    customer_id: Optional[int] = None
    start_date: datetime
    end_date: datetime
    usage_limit: Optional[int] = None
    times_used: int = Field(0, ge=0)
    is_active: bool = True
    business_id: Optional[int] = None


class PromotionUpdate(BaseModel):
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


class PromotionResponse(AuditMixin):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    promo_type: str = 'BuyXGetY'
    buy_product_id: Optional[int] = None
    buy_product_name: Optional[str] = None
    buy_quantity: float = 1.0
    get_product_id: Optional[int] = None
    get_product_name: Optional[str] = None
    get_quantity: float = 1.0
    get_discount_percentage: float = 100.0
    customer_group: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    start_date: datetime
    end_date: datetime
    usage_limit: Optional[int] = None
    times_used: int = 0
    is_active: bool = True


# Aliases for Promotional Rule terminology
PromotionalRuleCreate = PromotionCreate
PromotionalRuleUpdate = PromotionUpdate
PromotionalRuleResponse = PromotionResponse
