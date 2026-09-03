from typing import Optional, List
from pydantic import BaseModel, Field


class PosCartItem(BaseModel):
    product_id: int
    product_name: str
    qty: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)


class PosCheckoutRequest(BaseModel):
    cart_items: List[PosCartItem]
    customer_id: Optional[int] = None
    customer_name: str = "Walk-in Customer"
    warehouse_id: int = 1
    payment_method: str = "Cash"
    cash_amount: float = 0.0
    card_amount: float = 0.0
    print_receipt: bool = True
    kick_drawer: bool = False
    notes: Optional[str] = None
    business_id: Optional[int] = None


class PosCheckoutResponse(BaseModel):
    success: bool
    order_id: int
    order_number: str
    grand_total: float
    subtotal: float = 0.0
    tax: float = 0.0
    cash_amount: float = 0.0
    card_amount: float = 0.0
    change_due: float = 0.0
    payment_status: str = "Paid"
    print_receipt: bool = True
    kick_drawer: bool = False
    message: str

