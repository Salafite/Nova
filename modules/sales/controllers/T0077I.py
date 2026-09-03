from typing import Optional
from fastapi import APIRouter
from modules.sales.models.delivery import DeliveryCreate, DeliveryUpdate, DeliveryResponse
from modules.sales.services.delivery_service import DeliveryService, delivery_service, DELIVERY_REPO
from modules.core.controllers.base import create_crud_router
from modules.sales.controllers.pod_controller import (
    capture_pod_endpoint,
    log_cod_collection_endpoint,
)
service = delivery_service
router = create_crud_router('/api/T0077I', 'T0077 - Deliveries', service,
                            DeliveryCreate, DeliveryUpdate, DeliveryResponse)

@router.post('/{id}/pod')
def capture_pod(id: int, payload: dict):
    return service.capture_pod(
        delivery_id=id,
        signature=payload.get('signature') or payload.get('recipient_signature'),
        photo_url=payload.get('photo_url') or payload.get('delivery_photo_url'),
        location=payload.get('location') or payload.get('delivery_location'),
        timestamp=payload.get('timestamp') or payload.get('pod_timestamp'),
    )

@router.post('/{id}/cod')
def log_cod_collection(id: int, payload: dict):
    return service.log_cod_collection(
        delivery_id=id,
        cash_amount=payload.get('cash_amount') or payload.get('cod_cash_amount') or 0.0,
        check_amount=payload.get('check_amount') or payload.get('cod_check_amount') or 0.0,
        check_number=payload.get('check_number') or payload.get('cod_check_number'),
        check_bank=payload.get('check_bank') or payload.get('cod_check_bank'),
        payment_status=payload.get('payment_status'),
    )

handover_router = APIRouter(prefix='/api/sales/driver-handover', tags=['Driver Handover'])

@handover_router.get('/{driver_id}')
def get_driver_handover_report(driver_id: int, delivery_date: Optional[str] = None):
    return service.get_driver_handover_report(driver_id=driver_id, delivery_date=delivery_date)

@handover_router.post('/reconcile')
def reconcile_driver_cash(payload: dict):
    return service.reconcile_driver_cash(
        driver_id=payload.get('driver_id'),
        delivery_date=payload.get('delivery_date'),
        cash_submitted=payload.get('cash_submitted', 0.0),
        check_submitted=payload.get('check_submitted', 0.0),
        delivery_ids=payload.get('delivery_ids'),
        notes=payload.get('notes'),
    )

@router.get('/driver-handover/{driver_id}')
def get_driver_handover_report_alt(driver_id: int, delivery_date: Optional[str] = None):
    return service.get_driver_handover_report(driver_id=driver_id, delivery_date=delivery_date)

@router.post('/driver-handover/reconcile')
def reconcile_driver_cash_alt(payload: dict):
    return service.reconcile_driver_cash(
        driver_id=payload.get('driver_id'),
        delivery_date=payload.get('delivery_date'),
        cash_submitted=payload.get('cash_submitted', 0.0),
        check_submitted=payload.get('check_submitted', 0.0),
        delivery_ids=payload.get('delivery_ids'),
        notes=payload.get('notes'),
    )
