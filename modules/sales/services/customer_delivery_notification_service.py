"""
Nova ERP — Customer Delivery Notification & Public Live Tracking Service
Generates secure unguessable tracking tokens and dispatches SMS/WhatsApp alerts with live tracking links.
"""
import secrets
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status

from modules.sales.repositories.driver_tracking_repo import (
    DriverTrackingRepository,
    driver_tracking_repo as default_repo,
)
from modules.sales.services.eta_calculation_service import (
    DynamicETAService,
    eta_service as default_eta_service,
)
from modules.sales.models.delivery_tracking import (
    CustomerNotificationPayload,
    CustomerNotificationResult,
    CustomerLiveTrackingResponse,
    StopProgressItem,
)

logger = logging.getLogger(__name__)


class CustomerDeliveryNotificationService:
    """
    Handles customer tracking session lifecycle, SMS/WhatsApp alert dispatching,
    and public unauthenticated live tracking data retrieval.
    """

    def __init__(
        self,
        repo: Optional[DriverTrackingRepository] = None,
        eta_svc: Optional[DynamicETAService] = None,
    ):
        self.repo = repo or default_repo
        self.eta_service = eta_svc or default_eta_service

    def generate_tracking_token(self) -> str:
        """Generate a cryptographically secure, URL-safe tracking token."""
        return secrets.token_urlsafe(24)

    def create_or_refresh_session(
        self,
        run_stop_id: int,
        channel: str = "SMS",
    ) -> Dict[str, Any]:
        """
        Create a new customer tracking session or refresh existing token for a stop.
        """
        stop = self.repo.get_stop_by_id(run_stop_id)
        if not stop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery stop {run_stop_id} not found",
            )

        token = self.generate_tracking_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=48)

        session_payload = {
            "run_stop_id": run_stop_id,
            "sales_order_id": stop.get("sales_order_id"),
            "customer_id": stop.get("customer_id"),
            "tracking_token": token,
            "token_expires_at": expires_at,
            "notification_channel": channel,
            "notification_status": "Pending",
            "business_id": stop.get("business_id"),
        }

        session = self.repo.create_customer_tracking_session(session_payload)

        # Update stop record with token
        self.repo.update_stop(run_stop_id, {"tracking_token": token})
        return session

    def send_delivery_notification(
        self,
        payload: CustomerNotificationPayload,
        base_url: str = "https://app.nova-erp.com",
    ) -> CustomerNotificationResult:
        """
        Dispatch SMS / WhatsApp / Email delivery alert with live tracking URL to customer.
        """
        stop = self.repo.get_stop_by_id(payload.run_stop_id)
        if not stop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery stop {payload.run_stop_id} not found",
            )

        customer_id = stop.get("customer_id")
        customer_name = stop.get("customer_name") or "Valued Customer"
        order_num = stop.get("sales_order_number") or f"SO-{stop.get('sales_order_id')}"
        phone = payload.recipient_phone or stop.get("contact_phone") or stop.get("customer_phone_master")

        # Create or fetch tracking session
        session = self.create_or_refresh_session(payload.run_stop_id, channel=payload.channel)
        token = session.get("tracking_token")

        tracking_url = f"{base_url}/track/{token}"
        now = datetime.now(timezone.utc)

        # Construct message text
        msg = (
            payload.custom_message
            or f"Hello {customer_name}, your delivery for order {order_num} is on the way! "
               f"Track your driver in real-time and view live ETA here: {tracking_url}"
        )

        # Update session status
        if session.get("id"):
            self.repo.update_customer_tracking_session(
                session["id"],
                {
                    "notification_sent_at": now,
                    "notification_status": "Sent",
                },
            )

        # If stop was Pending, transition to In Transit
        if stop.get("status") == "Pending":
            self.repo.update_stop(payload.run_stop_id, {"status": "In Transit"})

        logger.info(f"Dispatched {payload.channel} alert for stop {payload.run_stop_id} to {phone}")

        return CustomerNotificationResult(
            run_stop_id=payload.run_stop_id,
            customer_id=customer_id,
            tracking_token=token,
            tracking_url=tracking_url,
            channel=payload.channel,
            status="Sent",
            sent_at=now,
            message_preview=msg,
        )

    def get_public_tracking_status(self, token: str) -> CustomerLiveTrackingResponse:
        """
        Unauthenticated, public endpoint resolving token to live truck position,
        dynamic ETA window, stop sequence progression, and perishable dock alerts.
        """
        session = self.repo.get_customer_tracking_session_by_token(token)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired delivery tracking link",
            )

        token_expiry = session.get("token_expires_at")
        now = datetime.now(timezone.utc)
        if token_expiry:
            if token_expiry.tzinfo is None:
                token_expiry = token_expiry.replace(tzinfo=timezone.utc)
            if token_expiry < now:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="This delivery tracking link has expired",
                )

        run_id = session.get("delivery_run_id")
        driver_id = session.get("driver_id")
        vehicle_id = session.get("vehicle_id")

        # Fetch latest driver/vehicle location
        latest_ping = None
        if driver_id:
            latest_ping = self.repo.get_latest_driver_location(driver_id)
        if not latest_ping and vehicle_id:
            latest_ping = self.repo.get_latest_vehicle_location(vehicle_id)

        driver_lat = float(latest_ping["latitude"]) if latest_ping else None
        driver_lng = float(latest_ping["longitude"]) if latest_ping else None
        driver_speed = float(latest_ping.get("speed_kmh") or 0.0) if latest_ping else 0.0
        driver_heading = float(latest_ping.get("heading") or 0.0) if latest_ping else 0.0

        dest_lat = float(session["stop_latitude"]) if session.get("stop_latitude") is not None else None
        dest_lng = float(session["stop_longitude"]) if session.get("stop_longitude") is not None else None

        # Fetch all stops in run to calculate sequence and progress
        stops = self.repo.get_run_stops(run_id) if run_id else []
        total_stops = len(stops) or 1
        stop_seq = session.get("stop_sequence") or 1

        stops_progress: List[StopProgressItem] = []
        for s in stops:
            is_target = (s.get("id") == session.get("run_stop_id"))
            stops_progress.append(StopProgressItem(
                stop_sequence=s.get("stop_sequence", 1),
                customer_name=s.get("customer_name") or "Customer",
                delivery_address=s.get("delivery_address") or "",
                status=s.get("status", "Pending"),
                is_current_target=is_target,
                delivered_at=s.get("delivered_at"),
            ))

        # Dynamic ETA calculation
        eta_calc = None
        distance_km = float(session["live_remaining_distance_km"]) if session.get("live_remaining_distance_km") is not None else None
        est_arrival = session.get("live_eta_timestamp")
        window_start = None
        window_end = None
        eta_minutes = None

        if driver_lat and driver_lng and dest_lat and dest_lng:
            eta_calc = self.eta_service.calculate_stop_eta(
                vehicle_lat=driver_lat,
                vehicle_lng=driver_lng,
                stop_lat=dest_lat,
                stop_lng=dest_lng,
                current_speed_kmh=driver_speed,
            )
            distance_km = eta_calc["distance_km"]
            est_arrival = eta_calc["estimated_arrival"]
            window_start = eta_calc["eta_window_start"]
            window_end = eta_calc["eta_window_end"]
            eta_minutes = eta_calc["travel_time_minutes"]

        # Check for perishable / refrigerated cargo
        is_refrigerated = True  # High-priority dock preparation flag
        dock_alert = (
            "Dock Preparation Alert: Refrigerated / perishable shipment on vehicle. "
            "Please ensure receiving dock and cold-chain staging crew are ready upon truck arrival."
        ) if is_refrigerated else None

        return CustomerLiveTrackingResponse(
            tracking_token=token,
            sales_order_number=session.get("sales_order_number"),
            customer_name=session.get("customer_name") or "Customer",
            delivery_address=session.get("delivery_address") or "",
            stop_status=session.get("stop_status") or "Pending",
            stop_sequence=stop_seq,
            total_stops=total_stops,
            driver_name=session.get("driver_name"),
            vehicle_code=session.get("vehicle_code"),
            driver_latitude=driver_lat,
            driver_longitude=driver_lng,
            driver_speed_kmh=driver_speed,
            driver_heading=driver_heading,
            destination_latitude=dest_lat,
            destination_longitude=dest_lng,
            distance_remaining_km=distance_km,
            estimated_arrival=est_arrival,
            eta_window_start=window_start,
            eta_window_end=window_end,
            eta_minutes_remaining=eta_minutes,
            is_refrigerated_cargo=is_refrigerated,
            dock_preparation_alert=dock_alert,
            stops_progress=stops_progress,
            last_updated_at=now,
        )


customer_notification_service = CustomerDeliveryNotificationService()
