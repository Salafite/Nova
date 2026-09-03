from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class BatchShelfLifeMetrics(BaseModel):
    batch_id: int = Field(..., description="ID of the batch (t0088)")
    batch_number: str = Field(..., description="Batch number designation")
    product_id: int = Field(..., description="ID of the product (SKU)")
    product_name: Optional[str] = Field(None, description="Name of the product")
    warehouse_id: Optional[int] = Field(None, description="ID of the warehouse holding the batch")
    warehouse_name: Optional[str] = Field(None, description="Name of the warehouse")
    manufacture_date: Optional[date] = Field(None, description="Manufacturing date of the batch")
    expiry_date: date = Field(..., description="Expiration date of the batch")
    days_to_expiry: int = Field(..., description="Days remaining until expiry")
    current_quantity: float = Field(..., description="Current available batch quantity")


class SpoilageRiskAlert(BaseModel):
    batch_id: int = Field(..., description="ID of the batch")
    batch_number: str = Field(..., description="Batch number designation")
    product_id: int = Field(..., description="Product ID")
    product_name: Optional[str] = Field(None, description="Product name")
    warehouse_id: Optional[int] = Field(None, description="Warehouse ID")
    warehouse_name: Optional[str] = Field(None, description="Warehouse name")
    current_quantity: float = Field(..., description="Current stock quantity in batch")
    expiry_date: date = Field(..., description="Expiration date")
    days_to_expiry: int = Field(..., description="Days remaining until expiration")
    daily_consumption_velocity: float = Field(..., description="Projected daily consumption velocity for this SKU")
    projected_consumption_units: float = Field(..., description="Units projected to be consumed before expiry")
    estimated_spoilage_quantity: float = Field(..., description="Units projected to expire before sale")
    spoilage_risk_percentage: float = Field(..., description="Percentage of batch projected to spoil (0-100%)")
    risk_severity: str = Field(..., description="Risk severity tier: 'low', 'medium', 'high', 'critical'")
    recommended_discount_percentage: float = Field(..., description="Recommended promotional discount % (e.g. 15, 30, 50)")
    recommended_action: str = Field(..., description="Actionable recommendation (e.g., 'Apply 30% markdown promotion')")


class BatchDiscountPromotionProposal(BaseModel):
    proposal_id: Optional[str] = Field(None, description="ID of the discount proposal")
    batch_id: int = Field(..., description="ID of the batch to apply promotion")
    batch_number: str = Field(..., description="Batch number")
    product_id: int = Field(..., description="Product ID")
    product_name: Optional[str] = Field(None, description="Product name")
    current_price: float = Field(..., description="Current list price")
    discount_percentage: float = Field(..., description="Proposed discount percentage")
    discounted_price: float = Field(..., description="New promotional price after discount")
    estimated_units_saved: float = Field(..., description="Estimated units saved from spoilage")
    estimated_revenue_recovered: float = Field(..., description="Estimated revenue recovered")
    effective_start_date: date = Field(..., description="Promotion start date")
    effective_end_date: date = Field(..., description="Promotion end date (batch expiry)")


class SpoilageRiskSummaryResponse(BaseModel):
    total_batches_analyzed: int = Field(..., description="Total perishable batches analyzed")
    at_risk_batches_count: int = Field(..., description="Number of batches with spoilage risk")
    total_estimated_spoilage_quantity: float = Field(..., description="Total quantity estimated to spoil")
    alerts: List[SpoilageRiskAlert] = Field(default_factory=list, description="List of spoilage risk alerts")
