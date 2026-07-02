from typing import Optional
from pydantic import Field
from models.factory import crud_model


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
