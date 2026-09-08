from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin
from modules.core.models.factory import crud_model


CustomerCreate, CustomerUpdate, CustomerResponse = crud_model('Customer', [
    ('name', str, Field(..., max_length=200)),
    ('group_name', str, 'Retail'),
    ('phone', Optional[str], Field(None, max_length=30)),
    ('email', Optional[str], Field(None, max_length=200)),
    ('credit_limit', float, Field(0, ge=0)),
    ('balance', float, Field(0, ge=0)),
    ('is_active', bool, True),
    ('default_price_list_id', Optional[int], None),
    ('default_tax_rate_id', Optional[int], None),
    ('payment_term_id', Optional[int], None),
    ('min_order_amount', float, Field(0, ge=0)),
    ('order_cutoff_time', Optional[str], Field(None, max_length=10)),
    ('allow_reorders', bool, True),
])

SupplierCreate, SupplierUpdate, SupplierResponse = crud_model('Supplier', [
    ('name', str, Field(..., max_length=200)),
    ('category', Optional[str], Field(None, max_length=100)),
    ('phone', Optional[str], Field(None, max_length=30)),
    ('email', Optional[str], Field(None, max_length=200)),
    ('payment_terms', Optional[str], Field(None, max_length=100)),
    ('rating', int, Field(0, ge=0, le=5)),
    ('is_active', bool, True),
])


class CustomerContractCreate(BaseModel):
    contract_number: Optional[str] = None
    customer_id: int
    product_id: int
    contracted_price: float = Field(..., ge=0)
    discount_percentage: float = Field(0.0, ge=0, le=100)
    min_order_quantity: float = Field(1.0, ge=0)
    start_date: date
    end_date: Optional[date] = None
    status: str = 'Active'
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
    discount_percentage: float = 0.0
    min_order_quantity: float = 1.0
    start_date: date
    end_date: Optional[date] = None
    status: str = 'Active'
    is_active: bool = True
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
