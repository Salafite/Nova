from typing import Optional
from pydantic import BaseModel, Field, computed_field
from modules.core.models.base import AuditMixin

class StockLevelCreate(BaseModel):
    product_id: int
    warehouse_id: int
    qty: float = Field(default=0, ge=0)
    reserved_qty: float = Field(default=0, ge=0)
    in_transit_qty: float = Field(default=0, ge=0)
    reorder_level: float = Field(default=0, ge=0)
    business_id: Optional[int] = None

class StockLevelUpdate(BaseModel):
    product_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    qty: Optional[float] = Field(None, ge=0)
    reserved_qty: Optional[float] = Field(None, ge=0)
    in_transit_qty: Optional[float] = Field(None, ge=0)
    reorder_level: Optional[float] = Field(None, ge=0)
    business_id: Optional[int] = None

class StockLevelResponse(AuditMixin):
    id: int
    product_id: int
    warehouse_id: int
    qty: float
    reserved_qty: float = 0
    in_transit_qty: float = 0
    reorder_level: float
    is_catch_weight: Optional[bool] = False
    nominal_weight: Optional[float] = None
    nominal_total_weight: Optional[float] = None
    actual_total_weight: Optional[float] = None
    pricing_uom_id: Optional[int] = None
    pricing_uom_code: Optional[str] = None
    inventory_value: Optional[float] = None

    @computed_field
    @property
    def available_qty(self) -> float:
        return max(0, self.qty - self.reserved_qty)


class DualBalanceResponse(BaseModel):
    id: Optional[int] = None
    product_id: int
    warehouse_id: int
    product_name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    warehouse_name: Optional[str] = None
    # Discrete Unit / Package Balances
    qty: float = Field(default=0.0, description="On-hand discrete unit/package balance (e.g. cases, wheels, units)")
    reserved_qty: float = Field(default=0.0, description="Reserved discrete units")
    in_transit_qty: float = Field(default=0.0, description="In-transit discrete units")
    available_qty: float = Field(default=0.0, description="Available discrete units")
    reorder_level: float = Field(default=0.0, description="Reorder level threshold in discrete units")
    # Catch Weight & Dual UOM Configuration
    is_catch_weight: bool = Field(default=False, description="Whether product uses dual UOM / catch-weight pricing")
    pricing_uom_id: Optional[int] = Field(None, description="Pricing unit of measure ID")
    pricing_uom_code: Optional[str] = Field(None, description="Pricing unit of measure code (e.g. kg, lb)")
    pricing_basis: Optional[str] = Field(default="weight", description="Pricing basis: weight or unit")
    nominal_weight: Optional[float] = Field(None, description="Nominal weight per discrete unit")
    tolerance_pct: Optional[float] = Field(None, description="Allowable weight variance percentage (+/-)")
    # Weight Balances (for catch-weight products)
    nominal_total_weight: float = Field(default=0.0, description="Nominal aggregate weight on hand")
    nominal_reserved_weight: float = Field(default=0.0, description="Nominal aggregate reserved weight")
    nominal_available_weight: float = Field(default=0.0, description="Nominal aggregate available weight")
    nominal_in_transit_weight: float = Field(default=0.0, description="Nominal aggregate in-transit weight")
    actual_total_weight: float = Field(default=0.0, description="Actual aggregate scale weight on hand")
    actual_reserved_weight: float = Field(default=0.0, description="Actual aggregate reserved weight")
    actual_available_weight: float = Field(default=0.0, description="Actual aggregate available weight")
    actual_in_transit_weight: float = Field(default=0.0, description="Actual aggregate in-transit weight")
    weight_variance: float = Field(default=0.0, description="Variance between actual and nominal weight (actual - nominal)")
    weight_variance_pct: float = Field(default=0.0, description="Variance percentage vs nominal weight")
    # Valuation
    cost_price: float = Field(default=0.0, description="Cost price per unit or per pricing UOM")
    nominal_valuation: float = Field(default=0.0, description="Inventory valuation based on nominal weights")
    actual_valuation: float = Field(default=0.0, description="Inventory valuation based on actual scale weights")
    valuation_difference: float = Field(default=0.0, description="Net valuation difference (actual - nominal)")
    inventory_value: float = Field(default=0.0, description="Primary balance sheet inventory asset value")


class InventoryValuationItem(BaseModel):
    product_id: int
    product_name: str
    sku: str
    warehouse_id: int
    warehouse_name: Optional[str] = None
    category: Optional[str] = None
    is_catch_weight: bool = False
    qty: float = 0.0
    nominal_weight: Optional[float] = None
    nominal_total_weight: float = 0.0
    actual_total_weight: float = 0.0
    pricing_uom_code: Optional[str] = None
    pricing_basis: Optional[str] = "weight"
    cost_price: float = 0.0
    nominal_valuation: float = 0.0
    actual_valuation: float = 0.0
    valuation_difference: float = 0.0
    inventory_value: float = 0.0


class InventoryValuationSummary(BaseModel):
    total_items_count: int = 0
    catch_weight_items_count: int = 0
    standard_items_count: int = 0
    total_discrete_qty: float = 0.0
    total_nominal_weight: float = 0.0
    total_actual_weight: float = 0.0
    total_weight_variance: float = 0.0
    total_nominal_valuation: float = 0.0
    total_actual_valuation: float = 0.0
    net_valuation_adjustment: float = 0.0
    total_inventory_value: float = 0.0
    items: list[InventoryValuationItem] = Field(default_factory=list)

