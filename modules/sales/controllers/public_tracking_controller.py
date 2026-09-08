"""
Nova ERP — Public Customer Live Delivery Tracking Controller
Exposes unauthenticated secure endpoint for end customers and supermarket receiving clerks
to view live driver truck location, remaining distance, dynamic ETA countdown, and cold chain alerts.
"""
import logging
from fastapi import APIRouter, HTTPException, status

from modules.sales.models.delivery_tracking import CustomerLiveTrackingResponse
from modules.sales.services.customer_delivery_notification_service import (
    CustomerDeliveryNotificationService,
    customer_notification_service as default_notification_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/public/tracking",
    tags=["Public Customer Live Delivery Tracking"],
)

_notification_service: CustomerDeliveryNotificationService = default_notification_service


@router.get(
    "/{tracking_token}",
    response_model=CustomerLiveTrackingResponse,
    summary="Get live customer delivery tracking by secure token",
    description="Unauthenticated endpoint providing real-time truck position, dynamic ETA window, stop progression, and dock preparation alerts.",
)
def get_public_customer_tracking(
    tracking_token: str,
) -> CustomerLiveTrackingResponse:
    """Resolve public customer tracking token to live delivery status."""
    try:
        return _notification_service.get_public_tracking_status(tracking_token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching public tracking for token {tracking_token}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tracking information: {str(e)}",
        ) from e
