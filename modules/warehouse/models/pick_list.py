from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin

class PickListCreate(BaseModel):
    pick_list_number: Optional[str] = Field(None, max_length=50)
    sales_order_id: int
    warehouse_id: Optional[int] = None
    status: str = 'Pending'
    notes: Optional[str] = None
    business_id: Optional[int] = None

class PickListUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    business_id: Optional[int] = None

class PickListResponse(AuditMixin):
    id: int
    pick_list_number: str
    sales_order_id: int
    warehouse_id: Optional[int] = None
    status: str
    notes: Optional[str] = None

class PickListItemCreate(BaseModel):
    pick_list_id: int
    sales_order_line_id: Optional[int] = None
    product_id: int
    product_name: Optional[str] = None
    qty_ordered: float = Field(default=0, ge=0)
    qty_picked: float = Field(default=0, ge=0)
    line_number: int = 1
    batch_id: Optional[int] = None
    batch_number: Optional[str] = Field(None, max_length=255)
    expiry_date: Optional[date] = None
    picked_batch_id: Optional[int] = None
    picked_batch_number: Optional[str] = Field(None, max_length=255)
    catch_weight_actual: Optional[float] = Field(None, ge=0)
    catch_weight_uom: Optional[str] = Field(None, max_length=50)
    nominal_weight: Optional[float] = Field(None, ge=0)
    tolerance_pct: Optional[float] = Field(None, ge=0, le=100)
    tolerance_variance_pct: Optional[float] = None
    tolerance_status: Optional[str] = Field(default='Not Applicable', max_length=30)
    supervisor_approved: bool = False
    supervisor_approved_by: Optional[int] = None
    supervisor_approved_at: Optional[datetime] = None
    supervisor_notes: Optional[str] = None

class PickListItemUpdate(BaseModel):
    qty_picked: Optional[float] = Field(None, ge=0)
    batch_id: Optional[int] = None
    batch_number: Optional[str] = Field(None, max_length=255)
    expiry_date: Optional[date] = None
    picked_batch_id: Optional[int] = None
    picked_batch_number: Optional[str] = Field(None, max_length=255)
    catch_weight_actual: Optional[float] = Field(None, ge=0)
    catch_weight_uom: Optional[str] = Field(None, max_length=50)
    nominal_weight: Optional[float] = Field(None, ge=0)
    tolerance_pct: Optional[float] = Field(None, ge=0, le=100)
    tolerance_variance_pct: Optional[float] = None
    tolerance_status: Optional[str] = Field(None, max_length=30)
    supervisor_approved: Optional[bool] = None
    supervisor_approved_by: Optional[int] = None
    supervisor_approved_at: Optional[datetime] = None
    supervisor_notes: Optional[str] = None

class PickListItemResponse(AuditMixin):
    id: int
    pick_list_id: int
    sales_order_line_id: Optional[int] = None
    product_id: int
    product_name: Optional[str] = None
    qty_ordered: float
    qty_picked: float
    line_number: int
    batch_id: Optional[int] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None
    picked_batch_id: Optional[int] = None
    picked_batch_number: Optional[str] = None
    catch_weight_actual: Optional[float] = None
    catch_weight_uom: Optional[str] = None
    nominal_weight: Optional[float] = None
    tolerance_pct: Optional[float] = None
    tolerance_variance_pct: Optional[float] = None
    tolerance_status: Optional[str] = 'Not Applicable'
    supervisor_approved: bool = False
    supervisor_approved_by: Optional[int] = None
    supervisor_approved_at: Optional[datetime] = None
    supervisor_notes: Optional[str] = None


class PickItemRequest(BaseModel):
    """Payload for picking a single pick list item with optional scale weight capture."""
    qty_picked: float = Field(..., ge=0)
    picked_batch_id: Optional[int] = None
    picked_batch_number: Optional[str] = Field(None, max_length=255)
    catch_weight_actual: Optional[float] = Field(None, ge=0)
    catch_weight_uom: Optional[str] = Field(None, max_length=50)
    nominal_weight: Optional[float] = Field(None, ge=0)
    tolerance_pct: Optional[float] = Field(None, ge=0, le=100)
    barcode: Optional[str] = Field(None, max_length=255)


# Alias for explicit clarity
PickItemWeightCaptureRequest = PickItemRequest


class ToleranceApprovalRequest(BaseModel):
    """Request payload for approving out-of-tolerance catch-weight items."""
    item_id: Optional[int] = None
    item_ids: Optional[List[int]] = None
    supervisor_id: Optional[int] = None
    supervisor_approved_by: Optional[int] = None
    approved_by: Optional[int] = None
    supervisor_notes: Optional[str] = None
    notes: Optional[str] = None


class ToleranceApprovalResponse(BaseModel):
    """Response payload after approving out-of-tolerance items."""
    approved_count: int = 0
    item_ids: List[int] = Field(default_factory=list)
    status: str = 'Approved'
    message: Optional[str] = None


class DiscrepancyItemResponse(BaseModel):
    """Representation of an individual pick list item discrepancy."""
    item_id: int
    product_id: int
    product_name: Optional[str] = None
    line_number: Optional[int] = None
    qty_ordered: float = 0
    qty_picked: float = 0
    nominal_weight: Optional[float] = None
    catch_weight_actual: Optional[float] = None
    catch_weight_uom: Optional[str] = None
    tolerance_pct: Optional[float] = None
    tolerance_variance_pct: Optional[float] = None
    tolerance_status: str = 'Within Tolerance'
    supervisor_approved: bool = False
    supervisor_approved_by: Optional[int] = None
    supervisor_approved_at: Optional[datetime] = None
    supervisor_notes: Optional[str] = None


class PickListDiscrepancyResponse(BaseModel):
    """Response payload containing summary and items for pick list discrepancies."""
    pick_list_id: int
    has_discrepancies: bool = False
    unapproved_count: int = 0
    discrepancies: List[DiscrepancyItemResponse] = Field(default_factory=list)


class PickListDetailResponse(PickListResponse):
    """Detailed pick list response including nested line items."""
    items: List[PickListItemResponse] = Field(default_factory=list)

