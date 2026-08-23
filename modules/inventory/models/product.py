from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class UOMCreate(BaseModel):
    uom_code: str = Field(..., max_length=10)
    uom_name: str = Field(..., max_length=50)
    category: str = 'Quantity'
    is_base_unit: bool = False
    is_active: bool = True

class UOMUpdate(BaseModel):
    uom_code: Optional[str] = Field(None, max_length=10)
    uom_name: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = None
    is_base_unit: Optional[bool] = None
    is_active: Optional[bool] = None

class UOMResponse(AuditMixin):
    id: int
    uom_code: str
    uom_name: str
    category: str
    is_base_unit: bool
    is_active: bool


class UOMConvCreate(BaseModel):
    from_uom_id: int
    to_uom_id: int
    factor: float = Field(..., gt=0)

class UOMConvUpdate(BaseModel):
    from_uom_id: Optional[int] = None
    to_uom_id: Optional[int] = None
    factor: Optional[float] = Field(None, gt=0)

class UOMConvResponse(AuditMixin):
    id: int
    from_uom_id: int
    to_uom_id: int
    factor: float


class ProductCreate(BaseModel):
    name: str = Field(..., max_length=200)
    sku: str = Field(..., max_length=50)
    barcode: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    type: str = Field(default='stockable', max_length=20)
    price: float = Field(default=0, ge=0)
    cost_price: Optional[float] = Field(default=0, ge=0)
    category: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    tax_rate: float = Field(default=0.05, ge=0)
    weight: float = Field(default=0, ge=0)
    volume: float = Field(default=0, ge=0)
    image_url: Optional[str] = Field(None, max_length=500)
    is_purchasable: bool = True
    is_saleable: bool = True
    is_active: bool = True
    is_catch_weight: bool = False
    pricing_uom_id: Optional[int] = None
    nominal_weight: Optional[float] = Field(None, ge=0)
    tolerance_pct: Optional[float] = Field(None, ge=0, le=100)
    pricing_basis: str = Field(default='weight', max_length=20)

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    sku: Optional[str] = Field(None, max_length=50)
    barcode: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    type: Optional[str] = Field(None, max_length=20)
    price: Optional[float] = Field(None, ge=0)
    cost_price: Optional[float] = Field(None, ge=0)
    category: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    tax_rate: Optional[float] = None
    weight: Optional[float] = Field(None, ge=0)
    volume: Optional[float] = Field(None, ge=0)
    image_url: Optional[str] = Field(None, max_length=500)
    is_purchasable: Optional[bool] = None
    is_saleable: Optional[bool] = None
    is_active: Optional[bool] = None
    is_catch_weight: Optional[bool] = None
    pricing_uom_id: Optional[int] = None
    nominal_weight: Optional[float] = Field(None, ge=0)
    tolerance_pct: Optional[float] = Field(None, ge=0, le=100)
    pricing_basis: Optional[str] = Field(None, max_length=20)

class ProductResponse(AuditMixin):
    id: int
    name: str
    sku: str
    barcode: Optional[str] = None
    description: Optional[str] = None
    type: str
    price: float
    cost_price: Optional[float] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    tax_rate: float
    weight: float
    volume: float
    image_url: Optional[str] = None
    is_purchasable: bool
    is_saleable: bool
    is_active: bool
    is_catch_weight: bool = False
    pricing_uom_id: Optional[int] = None
    nominal_weight: Optional[float] = None
    tolerance_pct: Optional[float] = None
    pricing_basis: Optional[str] = 'weight'


class BarcodeCreate(BaseModel):
    product_id: int
    barcode: str = Field(..., max_length=100)
    barcode_type: str = 'EAN13'
    is_primary: bool = False

class BarcodeUpdate(BaseModel):
    product_id: Optional[int] = None
    barcode: Optional[str] = Field(None, max_length=100)
    barcode_type: Optional[str] = None
    is_primary: Optional[bool] = None

class BarcodeResponse(AuditMixin):
    id: int
    product_id: int
    barcode: str
    barcode_type: str
    is_primary: bool


class AttrDefCreate(BaseModel):
    attribute_name: str = Field(..., max_length=50)
    attribute_type: str = 'Text'
    display_type: str = Field(default='select', max_length=20)
    description: Optional[str] = None
    is_required: bool = False
    create_variant: bool = True
    attribute_group: Optional[str] = Field(None, max_length=100)
    sort_order: int = 0
    is_active: bool = True

class AttrDefUpdate(BaseModel):
    attribute_name: Optional[str] = Field(None, max_length=50)
    attribute_type: Optional[str] = None
    display_type: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    is_required: Optional[bool] = None
    create_variant: Optional[bool] = None
    attribute_group: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class AttrDefResponse(AuditMixin):
    id: int
    attribute_name: str
    attribute_type: str
    display_type: str
    description: Optional[str]
    is_required: bool
    create_variant: bool
    attribute_group: Optional[str]
    sort_order: int
    is_active: bool


class AttrValueCreate(BaseModel):
    product_id: int
    attribute_id: int
    value_text: Optional[str] = None
    value_number: Optional[float] = None
    value_date: Optional[date] = None
    value_boolean: Optional[bool] = None

class AttrValueUpdate(BaseModel):
    product_id: Optional[int] = None
    attribute_id: Optional[int] = None
    value_text: Optional[str] = None
    value_number: Optional[float] = None
    value_date: Optional[date] = None
    value_boolean: Optional[bool] = None

class AttrValueResponse(AuditMixin):
    id: int
    product_id: int
    attribute_id: int
    value_text: Optional[str]
    value_number: Optional[float]
    value_date: Optional[date]
    value_boolean: Optional[bool]


class ProductUOMCreate(BaseModel):
    product_id: int
    base_uom_id: int
    purchase_uom_id: Optional[int] = None
    sales_uom_id: Optional[int] = None
    purchase_factor: float = 1
    sales_factor: float = 1
    is_catch_weight: bool = False
    pricing_uom_id: Optional[int] = None
    nominal_weight: Optional[float] = Field(None, ge=0)
    tolerance_pct: Optional[float] = Field(None, ge=0, le=100)
    pricing_basis: str = Field(default='weight', max_length=20)

class ProductUOMUpdate(BaseModel):
    product_id: Optional[int] = None
    base_uom_id: Optional[int] = None
    purchase_uom_id: Optional[int] = None
    sales_uom_id: Optional[int] = None
    purchase_factor: Optional[float] = None
    sales_factor: Optional[float] = None
    is_catch_weight: Optional[bool] = None
    pricing_uom_id: Optional[int] = None
    nominal_weight: Optional[float] = Field(None, ge=0)
    tolerance_pct: Optional[float] = Field(None, ge=0, le=100)
    pricing_basis: Optional[str] = Field(None, max_length=20)

class ProductUOMResponse(AuditMixin):
    id: int
    product_id: int
    base_uom_id: int
    purchase_uom_id: Optional[int] = None
    sales_uom_id: Optional[int] = None
    purchase_factor: float
    sales_factor: float
    is_catch_weight: bool = False
    pricing_uom_id: Optional[int] = None
    nominal_weight: Optional[float] = None
    tolerance_pct: Optional[float] = None
    pricing_basis: Optional[str] = 'weight'


class ProductTypeCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    color: str = '#6b7280'
    is_active: bool = True

class ProductTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None

class ProductTypeResponse(AuditMixin):
    id: int
    name: str
    code: Optional[str]
    description: Optional[str]
    color: str
    is_active: bool
