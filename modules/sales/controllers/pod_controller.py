import logging
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from packages.auth.deps import get_current_user
from modules.sales.services.delivery_service import delivery_service, DeliveryService
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

pod_router = APIRouter(prefix='/api/T0077I', tags=['T0077 - Deliveries POD'])
handover_router = APIRouter(prefix='/api/sales/driver-handover', tags=['Sales Driver Handover'])


class PodCaptureRequest(BaseModel):
    recipient_signature: Optional[str] = None
    delivery_photo_url: Optional[str] = None
    delivery_location: Optional[str] = Field(None, max_length=255)
    pod_timestamp: Optional[datetime] = None
    signature: Optional[str] = None
    photo_url: Optional[str] = None
    location: Optional[str] = None


class CodCollectionRequest(BaseModel):
    cod_cash_amount: float = Field(0.0, ge=0)
    cod_check_amount: float = Field(0.0, ge=0)
    cod_check_number: Optional[str] = Field(None, max_length=100)
    cod_check_bank: Optional[str] = Field(None, max_length=100)
    payment_status: Optional[str] = None


class DriverReconciliationRequest(BaseModel):
    driver_id: int
    received_cash: float = 0.0
    received_check: float = 0.0
    cash_submitted: Optional[float] = None
    check_submitted: Optional[float] = None
    delivery_date: Optional[date] = None
    handover_date: Optional[date] = None
    delivery_ids: Optional[List[int]] = None
    notes: Optional[str] = None


@pod_router.post('/{id}/pod')
def capture_pod_endpoint(
    id: int,
    body: PodCaptureRequest,
    user: dict = Depends(get_current_user),
):
    """
    Capture Proof of Delivery (POD) including recipient signature, delivery photo proof, and location.
    """
    sig = body.recipient_signature or body.signature
    photo = body.delivery_photo_url or body.photo_url
    loc = body.delivery_location or body.location
    return delivery_service.capture_pod(
        delivery_id=id,
        signature=sig,
        photo_url=photo,
        location=loc,
        timestamp=body.pod_timestamp,
    )


@pod_router.post('/{id}/cod')
def log_cod_collection_endpoint(
    id: int,
    body: CodCollectionRequest,
    user: dict = Depends(get_current_user),
):
    """
    Log Cash-On-Delivery (COD) collection (cash and/or check) at delivery time.
    """
    return delivery_service.log_cod_collection(
        delivery_id=id,
        cash_amount=body.cod_cash_amount,
        check_amount=body.cod_check_amount,
        check_number=body.cod_check_number,
        check_bank=body.cod_check_bank,
        payment_status=body.payment_status,
    )


@handover_router.get('/{driver_id}')
def get_driver_handover_report_endpoint(
    driver_id: int,
    handover_date: Optional[date] = Query(None, alias='delivery_date', description='Handover delivery date'),
    delivery_date: Optional[date] = Query(None, description='Alternative date param'),
    user: dict = Depends(get_current_user),
):
    """
    Retrieve end-of-day driver handover report summarizing total deliveries, completion, and COD cash/check collections.
    """
    target_date = handover_date or delivery_date
    return delivery_service.get_driver_handover_report(
        driver_id=driver_id,
        delivery_date=target_date,
    )


@handover_router.post('/reconcile')
def reconcile_driver_cash_endpoint(
    body: DriverReconciliationRequest,
    user: dict = Depends(get_current_user),
):
    """
    Reconcile driver collected cash and checks against submitted physical cash/checks at the depot.
    """
    cash_val = body.cash_submitted if body.cash_submitted is not None else body.received_cash
    check_val = body.check_submitted if body.check_submitted is not None else body.received_check
    target_date = body.handover_date or body.delivery_date

    return delivery_service.reconcile_driver_cash(
        driver_id=body.driver_id,
        delivery_date=target_date,
        cash_submitted=cash_val,
        check_submitted=check_val,
        delivery_ids=body.delivery_ids,
        notes=body.notes,
    )
