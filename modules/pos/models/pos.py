from typing import Optional, List
from pydantic import BaseModel, Field


class PosCartItem(BaseModel):
    product_id: int
    product_name: str
    qty: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)


class PosCheckoutRequest(BaseModel):
    cart_items: List[PosCartItem]
    customer_name: str = "Walk-in Customer"
    warehouse_id: int = 1
    payment_method: str = "Cash"
    notes: Optional[str] = None


class PosCheckoutResponse(BaseModel):
    success: bool
    order_id: int
    order_number: str
    grand_total: float
    message: str
