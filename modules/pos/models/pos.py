from typing import Optional, List
from pydantic import BaseModel, Field


class PosCartItem(BaseModel):
    product_id: int
    product_name: str
    qty: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    barcode: Optional[str] = None
    uom: Optional[str] = None


class PosPaymentSplit(BaseModel):
    payment_method: str = Field(..., description="Payment method name e.g. Cash, Card, Store Credit")
    amount: float = Field(..., ge=0, description="Amount allocated to this payment method")
    reference: Optional[str] = Field(None, description="Optional payment reference or transaction ID")


class PosCheckoutRequest(BaseModel):
    cart_items: List[PosCartItem]
    customer_id: Optional[int] = Field(None, description="Optional customer ID from t0010")
    customer_name: str = "Walk-in Customer"
    warehouse_id: int = 1
    payment_method: str = "Cash"
    payments: Optional[List[PosPaymentSplit]] = Field(default_factory=list, description="Split payment breakdown")
    amount_tendered: Optional[float] = Field(None, ge=0, description="Total cash/tendered amount provided by customer")
    notes: Optional[str] = None
    business_id: Optional[int] = None


class PosReceiptItem(BaseModel):
    product_id: int
    product_name: str
    qty: float
    unit_price: float
    line_total: float


class PosReceiptData(BaseModel):
    order_id: int
    order_number: str
    order_date: str
    customer_name: str
    customer_id: Optional[int] = None
    warehouse_id: int = 1
    items: List[PosReceiptItem] = Field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    grand_total: float = 0.0
    amount_tendered: float = 0.0
    change_due: float = 0.0
    kick_drawer: bool = False
    message: str

