import logging
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from modules.portal.repositories.portal_repo import PortalRepository
from modules.portal.services.portal_pricing_service import PortalPricingService
from modules.portal.models.portal import (
    PortalOrderCreate,
    PortalOrderLineCreate,
    PortalOrderResponse,
    PortalOrderLineResponse,
    PortalReorderRequest,
    PortalOrderCancelRequest,
    CutoffValidationResponse,
    OrderValidationResponse,
)

logger = logging.getLogger(__name__)


def _parse_delivery_date_from_notes(notes: Optional[str]) -> Optional[date]:
    """Extract delivery date tag [Delivery Date: YYYY-MM-DD] from order notes if present."""
    if not notes:
        return None
    match = re.search(r"\[Delivery Date:\s*(\d{4}-\d{2}-\d{2})\]", str(notes))
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except Exception:
            return None
    return None


def _format_time_str(time_val: Any) -> Optional[str]:
    """Normalize time string or time object to HH:MM format."""
    if not time_val:
        return None
    if isinstance(time_val, (time, datetime)):
        return time_val.strftime("%H:%M")
    s = str(time_val).strip()
    if not s:
        return None
    parts = s.split(":")
    if len(parts) >= 2:
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    return s


class PortalOrderService:
    """Service handling B2B replenishment order placement, cutoff time enforcement,
    minimum order threshold validation, order history queries, and 1-click reorders.
    """

    def __init__(
        self,
        portal_repo: Optional[PortalRepository] = None,
        pricing_service: Optional[PortalPricingService] = None,
    ):
        self.repo = portal_repo or PortalRepository()
        self.portal_repo = self.repo
        self.pricing_service = pricing_service or PortalPricingService(repo=self.repo)
        self.pricing_service.portal_repo = self.repo

    def validate_cutoff_time(
        self,
        customer_id: int,
        current_dt: Optional[datetime] = None,
        conn=None,
    ) -> CutoffValidationResponse:
        """Validate order submission against customer's daily ordering cutoff deadline."""
        customer = self.repo.get_customer_by_id(customer_id, conn=conn)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist.")

        if current_dt is None:
            current_dt = datetime.now(timezone.utc)

        cutoff_raw = customer.get("order_cutoff_time")
        cutoff_formatted = _format_time_str(cutoff_raw)
        current_time_str = current_dt.strftime("%H:%M")

        if cutoff_formatted:
            parts = cutoff_formatted.split(":")
            cutoff_hour, cutoff_minute = int(parts[0]), int(parts[1])
            is_past_cutoff = (current_dt.hour, current_dt.minute) > (cutoff_hour, cutoff_minute)

            if is_past_cutoff:
                next_delivery_date = current_dt.date() + timedelta(days=2)
                message = (
                    f"Daily cutoff time of {cutoff_formatted} has passed. "
                    f"Next scheduled delivery date is {next_delivery_date}."
                )
            else:
                next_delivery_date = current_dt.date() + timedelta(days=1)
                message = (
                    f"Order placed before {cutoff_formatted} cutoff. "
                    f"Scheduled for next-day delivery on {next_delivery_date}."
                )
        else:
            is_past_cutoff = False
            next_delivery_date = current_dt.date() + timedelta(days=1)
            message = (
                f"No daily cutoff time configured. "
                f"Order scheduled for next-day delivery on {next_delivery_date}."
            )

        return CutoffValidationResponse(
            is_past_cutoff=is_past_cutoff,
            cutoff_time=cutoff_formatted,
            current_time=current_time_str,
            current_timezone="UTC",
            next_delivery_date=next_delivery_date,
            message=message,
        )

    def validate_order(
        self,
        customer_id: int,
        items: List[Union[PortalOrderLineCreate, Dict[str, Any]]],
        current_dt: Optional[datetime] = None,
        conn=None,
    ) -> OrderValidationResponse:
        """Validate line items, calculate subtotal with contracted pricing, check minimum threshold and cutoff."""
        customer = self.repo.get_customer_by_id(customer_id, conn=conn)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist.")

        cutoff_status = self.validate_cutoff_time(customer_id, current_dt=current_dt, conn=conn)
        resolved_lines = self.pricing_service.resolve_line_items_pricing(customer_id, items, conn=conn)

        subtotal = sum(float(line.get("line_total") or 0.0) for line in resolved_lines)
        min_order_amount = float(customer.get("min_order_amount") or 0.0)
        meets_minimum = subtotal >= min_order_amount

        errors: List[str] = []
        warnings: List[str] = []

        if not meets_minimum:
            errors.append(
                f"Order subtotal ${subtotal:.2f} is below the minimum required order amount of ${min_order_amount:.2f}."
            )

        if cutoff_status.is_past_cutoff:
            warnings.append(
                f"Order placed after cutoff deadline ({cutoff_status.cutoff_time}). "
                f"Fulfillment scheduled for {cutoff_status.next_delivery_date}."
            )

        is_valid = len(errors) == 0

        return OrderValidationResponse(
            is_valid=is_valid,
            subtotal=round(subtotal, 2),
            min_order_amount=min_order_amount,
            meets_minimum=meets_minimum,
            cutoff_status=cutoff_status,
            errors=errors,
            warnings=warnings,
        )

    def create_order(
        self,
        customer_id: int,
        order_in: PortalOrderCreate,
        user_id: Optional[int] = None,
        current_dt: Optional[datetime] = None,
        conn=None,
    ) -> PortalOrderResponse:
        """Create a B2B sales order header (T0012) and line items (T0013) with contracted pricing."""
        customer = self.repo.get_customer_by_id(customer_id, conn=conn)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist.")

        if not customer.get("is_active", True):
            raise ValueError(f"Customer account {customer.get('name')} is inactive.")

        if not order_in.items:
            raise ValueError("Order must contain at least one line item.")

        if current_dt is None:
            current_dt = datetime.now(timezone.utc)

        cutoff_status = self.validate_cutoff_time(customer_id, current_dt=current_dt, conn=conn)
        requested_delivery_date = order_in.requested_delivery_date or cutoff_status.next_delivery_date

        resolved_lines = self.pricing_service.resolve_line_items_pricing(customer_id, order_in.items, conn=conn)
        subtotal = sum(float(line.get("line_total") or 0.0) for line in resolved_lines)
        min_order_amount = float(customer.get("min_order_amount") or 0.0)

        if min_order_amount > 0 and subtotal < min_order_amount:
            raise ValueError(
                f"Order subtotal ${subtotal:.2f} is below the minimum required order amount of ${min_order_amount:.2f}."
            )

        # Resolve warehouse
        warehouse_id = order_in.warehouse_id
        if not warehouse_id:
            active_wh = self.repo.get_active_warehouse(conn=conn)
            warehouse_id = active_wh["id"] if active_wh else None

        # Resolve tax rate
        tax_rate_id = customer.get("default_tax_rate_id")
        tax_rate_pct = 0.0
        if tax_rate_id:
            tr = self.repo.get_tax_rate(tax_rate_id, conn=conn)
            if tr:
                tax_rate_pct = float(tr.get("rate") or 0.0)

        tax_amount = round(subtotal * (tax_rate_pct / 100.0), 2)
        grand_total = round(subtotal + tax_amount, 2)

        delivery_tag = f"[Delivery Date: {requested_delivery_date.isoformat()}]"
        if order_in.notes:
            full_notes = f"{delivery_tag}\n{order_in.notes}"
        else:
            full_notes = delivery_tag

        order_data = {
            "customer_id": customer_id,
            "warehouse_id": warehouse_id,
            "subtotal": subtotal,
            "tax": tax_amount,
            "grand_total": grand_total,
            "status": order_in.status or "Confirmed",
            "order_date": current_dt.date(),
            "notes": full_notes,
            "price_list_id": customer.get("default_price_list_id"),
            "tax_rate_id": tax_rate_id,
            "payment_term_id": customer.get("payment_term_id"),
            "created_by": user_id,
            "updated_by": user_id,
        }

        created = self.repo.create_order(order_data, resolved_lines, conn=conn)
        return self._to_order_response(created, requested_delivery_date=requested_delivery_date)

    def get_orders(
        self,
        customer_id: int,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
        conn=None,
    ) -> Tuple[List[PortalOrderResponse], int]:
        """Fetch customer's order history with pagination."""
        orders_data, total = self.repo.get_orders(
            customer_id=customer_id,
            status=status,
            page=page,
            limit=limit,
            conn=conn,
        )
        responses = [self._to_order_response(o) for o in orders_data]
        return responses, total

    def get_order_by_id(
        self,
        customer_id: int,
        order_id: int,
        conn=None,
    ) -> Optional[PortalOrderResponse]:
        """Retrieve full details and line items for a specific customer order."""
        order_data = self.repo.get_order_by_id(order_id=order_id, customer_id=customer_id, conn=conn)
        if not order_data:
            return None
        return self._to_order_response(order_data)

    def reorder(
        self,
        customer_id: int,
        reorder_in: PortalReorderRequest,
        user_id: Optional[int] = None,
        current_dt: Optional[datetime] = None,
        conn=None,
    ) -> PortalOrderResponse:
        """Create a duplicate replenishment order based on past order history."""
        customer = self.repo.get_customer_by_id(customer_id, conn=conn)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist.")

        if not customer.get("is_active", True):
            raise ValueError("Customer account is inactive.")

        if not customer.get("allow_reorders", True):
            raise ValueError("Reordering is disabled for this customer account.")

        if not reorder_in.order_id:
            raise ValueError("order_id is required to duplicate past order.")

        original_order = self.repo.get_order_by_id(
            order_id=reorder_in.order_id,
            customer_id=customer_id,
            conn=conn,
        )
        if not original_order:
            raise ValueError(
                f"Original order #{reorder_in.order_id} not found or does not belong to customer."
            )

        raw_lines = original_order.get("lines") or []
        items = [
            PortalOrderLineCreate(
                product_id=line["product_id"],
                qty=float(line.get("qty") or 1.0),
                notes=line.get("notes"),
            )
            for line in raw_lines
            if line.get("product_id")
        ]

        if not items:
            raise ValueError("Original order has no valid line items to reorder.")

        reorder_notes = (
            reorder_in.notes
            or f"Replenishment reorder based on #{original_order.get('order_number', reorder_in.order_id)}"
        )

        order_create = PortalOrderCreate(
            items=items,
            warehouse_id=original_order.get("warehouse_id"),
            requested_delivery_date=reorder_in.requested_delivery_date,
            notes=reorder_notes,
            status=reorder_in.status or "Confirmed",
        )

        return self.create_order(
            customer_id=customer_id,
            order_in=order_create,
            user_id=user_id,
            current_dt=current_dt,
            conn=conn,
        )

    def cancel_order(
        self,
        customer_id: int,
        order_id: int,
        cancel_in: Optional[PortalOrderCancelRequest] = None,
        user_id: Optional[int] = None,
        conn=None,
    ) -> PortalOrderResponse:
        """Cancel an unfulfilled order (in Draft, Pending, or Confirmed status)."""
        order = self.repo.get_order_by_id(order_id=order_id, customer_id=customer_id, conn=conn)
        if not order:
            raise ValueError(f"Order #{order_id} not found.")

        current_status = order.get("status")
        if current_status not in ("Draft", "Pending", "Confirmed"):
            raise ValueError(f"Cannot cancel order in '{current_status}' status.")

        reason = cancel_in.reason if cancel_in and cancel_in.reason else "Cancelled by customer"
        old_notes = order.get("notes") or ""
        cancel_tag = f"[Cancelled by customer: {reason}]"
        new_notes = f"{old_notes}\n{cancel_tag}".strip() if old_notes else cancel_tag

        self.repo.update_order_status(
            order_id=order_id,
            status="Cancelled",
            notes=new_notes,
            customer_id=customer_id,
            conn=conn,
        )

        updated_order = self.get_order_by_id(customer_id=customer_id, order_id=order_id, conn=conn)
        if updated_order:
            return updated_order

        # Fallback if mock repo doesn't support re-fetching
        order_copy = dict(order)
        order_copy["status"] = "Cancelled"
        order_copy["notes"] = new_notes
        return self._to_order_response(order_copy)

    def _to_order_response(
        self,
        order_dict: Dict[str, Any],
        requested_delivery_date: Optional[date] = None,
    ) -> PortalOrderResponse:
        """Helper to convert dictionary to PortalOrderResponse model."""
        lines_data = order_dict.get("lines") or []
        lines = [
            PortalOrderLineResponse(
                id=line.get("id"),
                sales_order_id=line.get("sales_order_id", order_dict.get("id")),
                product_id=line.get("product_id"),
                product_code=line.get("product_code"),
                product_name=line.get("product_name") or f"Product #{line.get('product_id')}",
                uom_name=line.get("uom_name"),
                qty=float(line.get("qty") or 0.0),
                unit_price=float(line.get("unit_price") or 0.0),
                line_total=float(line.get("line_total") or 0.0),
                line_number=int(line.get("line_number") or 1),
            )
            for line in lines_data
        ]

        req_date = (
            requested_delivery_date
            or order_dict.get("requested_delivery_date")
            or _parse_delivery_date_from_notes(order_dict.get("notes"))
        )

        return PortalOrderResponse(
            id=order_dict["id"],
            order_number=order_dict.get("order_number") or f"SO-{order_dict['id']}",
            customer_id=order_dict.get("customer_id", 0),
            customer_name=order_dict.get("customer_name"),
            warehouse_id=order_dict.get("warehouse_id"),
            subtotal=float(order_dict.get("subtotal") or 0.0),
            tax=float(order_dict.get("tax") or 0.0),
            grand_total=float(order_dict.get("grand_total") or 0.0),
            status=order_dict.get("status") or "Confirmed",
            order_date=order_dict.get("order_date") or date.today(),
            requested_delivery_date=req_date,
            notes=order_dict.get("notes"),
            created_at=order_dict.get("created_at"),
            created_by=order_dict.get("created_by"),
            updated_at=order_dict.get("updated_at"),
            updated_by=order_dict.get("updated_by"),
            update_number=order_dict.get("update_number", 0),
            lines=lines,
        )
