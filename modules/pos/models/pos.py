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
    payments: List[PosPaymentSplit] = Field(default_factory=list)
    cashier_name: Optional[str] = "Cashier"
    business_name: Optional[str] = "Nova Wholesale Depot"


class PosCheckoutResponse(BaseModel):
    success: bool
    order_id: int
    order_number: str
    subtotal: Optional[float] = 0.0
    tax: Optional[float] = 0.0
    grand_total: float
    amount_tendered: Optional[float] = 0.0
    change_due: Optional[float] = 0.0
    payments: Optional[List[PosPaymentSplit]] = Field(default_factory=list)
    receipt: Optional[PosReceiptData] = None
    message: str


class PosCustomerLookup(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    customer_group: Optional[str] = None
    credit_limit: Optional[float] = 0.0
    current_balance: Optional[float] = 0.0


class PosBarcodeLookupResponse(BaseModel):
    product_id: int
    product_code: str
    barcode: Optional[str] = None
    product_name: str
    unit_price: float
    uom: Optional[str] = "PCS"
    stock_qty: float = 0.0
