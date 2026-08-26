"""
Nova ERP — Stock Transfers & Inter-Branch Replenishment Pydantic Models
"""
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin, TenantMixin


class StockTransferLineCreate(BaseModel):
    transfer_id: Optional[int] = None
    product_id: int
    qty_requested: float = Field(..., gt=0, description="Quantity requested for transfer")
    qty_dispatched: float = Field(default=0, ge=0, description="Quantity dispatched from source")
    qty_received: float = Field(default=0, ge=0, description="Quantity received at destination")
    qty_lost: float = Field(default=0, ge=0, description="Quantity lost/damaged in transit")
    loss_reason: Optional[str] = Field(None, max_length=100, description="Reason for discrepancy/loss")
    loss_notes: Optional[str] = Field(None, description="Detailed loss or discrepancy notes")
    batch_id: Optional[int] = Field(None, description="Batch reference if batch tracked")
    batch_number: Optional[str] = Field(None, max_length=100, description="Batch number string")
    line_number: int = Field(default=1, ge=1, description="Line number sequence")
    notes: Optional[str] = None
    is_active: bool = True
    business_id: Optional[int] = None


class StockTransferLineUpdate(BaseModel):
    transfer_id: Optional[int] = None
    product_id: Optional[int] = None
    qty_requested: Optional[float] = Field(None, gt=0)
    qty_dispatched: Optional[float] = Field(None, ge=0)
    qty_received: Optional[float] = Field(None, ge=0)
    qty_lost: Optional[float] = Field(None, ge=0)
    loss_reason: Optional[str] = Field(None, max_length=100)
    loss_notes: Optional[str] = None
    batch_id: Optional[int] = None
    batch_number: Optional[str] = Field(None, max_length=100)
    line_number: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None


class StockTransferLineResponse(AuditMixin):
    id: int
    transfer_id: int
    product_id: int
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    uom_name: Optional[str] = None
    qty_requested: float
    qty_dispatched: float = 0
    qty_received: float = 0
    qty_lost: float = 0
    loss_reason: Optional[str] = None
    loss_notes: Optional[str] = None
    batch_id: Optional[int] = None
    batch_number: Optional[str] = None
    line_number: int = 1
    notes: Optional[str] = None
    is_active: bool = True


class StockTransferCreate(BaseModel):
    transfer_number: Optional[str] = Field(None, max_length=50, description="Transfer number (auto-generated if omitted)")
    source_warehouse_id: int = Field(..., description="Source origin warehouse ID")
    destination_warehouse_id: int = Field(..., description="Destination receiving warehouse ID")
    status: str = Field(default="Draft", max_length=30, description="Transfer status")
    transfer_date: Optional[date] = Field(None, description="Date of transfer order")
    expected_delivery_date: Optional[date] = Field(None, description="Expected delivery date")
    carrier: Optional[str] = Field(None, max_length=100, description="Carrier / transport provider")
    tracking_number: Optional[str] = Field(None, max_length=100, description="Tracking or waybill number")
    dispatched_at: Optional[datetime] = None
    dispatched_by: Optional[int] = None
    received_at: Optional[datetime] = None
    received_by: Optional[int] = None
    notes: Optional[str] = None
    is_active: bool = True
    business_id: Optional[int] = None
    lines: Optional[List[StockTransferLineCreate]] = Field(default=None, description="Transfer line items")


class StockTransferUpdate(BaseModel):
    transfer_number: Optional[str] = Field(None, max_length=50)
    source_warehouse_id: Optional[int] = None
    destination_warehouse_id: Optional[int] = None
    status: Optional[str] = Field(None, max_length=30)
    transfer_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    carrier: Optional[str] = Field(None, max_length=100)
    tracking_number: Optional[str] = Field(None, max_length=100)
    dispatched_at: Optional[datetime] = None
    dispatched_by: Optional[int] = None
    received_at: Optional[datetime] = None
    received_by: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None
    lines: Optional[List[StockTransferLineCreate]] = None


class StockTransferResponse(AuditMixin):
    id: int
    transfer_number: str
    source_warehouse_id: int
    source_warehouse_name: Optional[str] = None
    destination_warehouse_id: int
    destination_warehouse_name: Optional[str] = None
    status: str
    transfer_date: date
    expected_delivery_date: Optional[date] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    dispatched_at: Optional[datetime] = None
    dispatched_by: Optional[int] = None
    dispatched_by_name: Optional[str] = None
    received_at: Optional[datetime] = None
    received_by: Optional[int] = None
    received_by_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    total_requested_qty: Optional[float] = 0
    total_dispatched_qty: Optional[float] = 0
    total_received_qty: Optional[float] = 0
    total_lost_qty: Optional[float] = 0
    lines_count: Optional[int] = 0
    lines: Optional[List[StockTransferLineResponse]] = None


class StockTransferDispatchLine(BaseModel):
    line_id: Optional[int] = None
    product_id: Optional[int] = None
    qty_dispatched: float = Field(..., gt=0, description="Dispatched quantity")
    batch_id: Optional[int] = None
    batch_number: Optional[str] = None


class StockTransferDispatch(BaseModel):
    carrier: Optional[str] = Field(None, max_length=100)
    tracking_number: Optional[str] = Field(None, max_length=100)
    dispatched_by: Optional[int] = None
    dispatched_at: Optional[datetime] = None
    notes: Optional[str] = None
    lines: Optional[List[StockTransferDispatchLine]] = None


class StockTransferLossDetail(BaseModel):
    line_id: Optional[int] = None
    product_id: Optional[int] = None
    qty_lost: float = Field(default=0, ge=0, description="Quantity lost or damaged")
    loss_reason: Optional[str] = Field(None, max_length=100, description="Transit Damage, Spillage, Theft, Expired, Other")
    loss_notes: Optional[str] = None


class StockTransferReceiveLine(BaseModel):
    line_id: Optional[int] = None
    product_id: Optional[int] = None
    qty_received: float = Field(..., ge=0, description="Quantity successfully received")
    qty_lost: float = Field(default=0, ge=0, description="Quantity damaged or lost during transit")
    loss_reason: Optional[str] = Field(None, max_length=100)
    loss_notes: Optional[str] = None
    batch_id: Optional[int] = None
    batch_number: Optional[str] = None


class StockTransferReceive(BaseModel):
    received_by: Optional[int] = None
    received_at: Optional[datetime] = None
    notes: Optional[str] = None
    lines: Optional[List[StockTransferReceiveLine]] = None
    losses: Optional[List[StockTransferLossDetail]] = None


class ReplenishmentSuggestionItem(BaseModel):
    product_id: int
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    destination_warehouse_id: int
    destination_warehouse_name: Optional[str] = None
    current_stock: float = 0
    reserved_stock: float = 0
    in_transit_stock: float = 0
    available_stock: float = 0
    reorder_point: float = 0
    safety_stock: float = 0
    suggested_transfer_qty: float = 0
    source_warehouse_id: Optional[int] = None
    source_warehouse_name: Optional[str] = None
    source_available_stock: Optional[float] = None
    priority: str = Field(default="Normal", description="Priority level: Critical, High, Normal, Low")
    reason: Optional[str] = None


class ReplenishmentSuggestionResponse(TenantMixin):
    total_suggestions: int = 0
    critical_count: int = 0
    high_count: int = 0
    items: List[ReplenishmentSuggestionItem] = Field(default_factory=list)
    generated_at: Optional[datetime] = None


class ReplenishmentGenerateItem(BaseModel):
    product_id: int
    destination_warehouse_id: int
    source_warehouse_id: int
    suggested_transfer_qty: float = Field(..., gt=0)
    batch_id: Optional[int] = None
    batch_number: Optional[str] = None


class ReplenishmentGenerateRequest(TenantMixin):
    source_warehouse_id: Optional[int] = None
    destination_warehouse_id: Optional[int] = None
    items: Optional[List[ReplenishmentGenerateItem]] = None
    transfer_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    carrier: Optional[str] = None
    notes: Optional[str] = None


class ReplenishmentGenerateResponse(BaseModel):
    transfers_created: int = 0
    transfer_ids: List[int] = Field(default_factory=list)
    transfer_numbers: List[str] = Field(default_factory=list)
    transfers: Optional[List[StockTransferResponse]] = None
