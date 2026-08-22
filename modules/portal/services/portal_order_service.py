import logging
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple, Union

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


def _parse_time(val: Any) -> Optional[Tuple[int, int]]:
    """Parse a time string or time object into (hour, minute) tuple."""
    if val is None:
        return None
    if isinstance(val, time):
        return val.hour, val.minute
    if isinstance(val, str):
        val_str = val.strip()
        parts = val_str.split(':')
        if len(parts) >= 2:
            try:
                return int(parts[0]), int(parts[1])
            except ValueError:
                return None
    return None


class PortalOrderService:
    """Service layer for B2B customer replenishment ordering, cutoff time enforcement,
    minimum order validation, 1-click reorders, and customer order management.
    """

    def __init__(
        self,
        portal_repo: Optional[PortalRepository] = None,
        pricing_service: Optional[PortalPricingService] = None
    ):
        self.portal_repo = portal_repo or PortalRepository()
        self.pricing_service = pricing_service or PortalPricingService(portal_repo=self.portal_repo)

    def validate_cutoff_time(
        self,
        customer_id: int,
        current_dt: Optional[datetime] = None,
        conn=None
    ) -> CutoffValidationResponse:
        """Validate current order placement time against customer's configured cutoff deadline.
        
        If an order is placed before the cutoff time (e.g. 22:00), it qualifies for next-day fulfillment (D+1).
        If placed after the cutoff time, fulfillment is scheduled for 2 days out (D+2).
        """
        customer = self.portal_repo.get_customer_by_id(customer_id, conn=conn)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist.")

        dt = current_dt or datetime.now(timezone.utc)
        current_time_str = dt.strftime('%H:%M')
        cutoff_raw = customer.get('order_cutoff_time')
        parsed_cutoff = _parse_time(cutoff_raw)

        if parsed_cutoff is not None:
            cutoff_hour, cutoff_min = parsed_cutoff
            cutoff_str = f"{cutoff_hour:02d}:{cutoff_min:02d}"
            cutoff_t = time(cutoff_hour, cutoff_min)
            current_t = dt.time()

            if current_t <= cutoff_t:
                is_past_cutoff = False
                next_delivery_date = dt.date() + timedelta(days=1)
                message = (
                    f"Order placed before {cutoff_str} cutoff. "
                    f"Scheduled for next-day delivery on {next_delivery_date.strftime('%Y-%m-%d')}."
                )
            else:
                is_past_cutoff = True
                next_delivery_date = dt.date() + timedelta(days=2)
                message = (
                    f"Order placed after {cutoff_str} cutoff deadline has passed. "
                    f"Fulfillment scheduled for delivery on {next_delivery_date.strftime('%Y-%m-%d')}."
                )
        else:
            is_past_cutoff = False
            cutoff_str = None
            next_delivery_date = dt.date() + timedelta(days=1)
            message = f"Standard delivery scheduled for {next_delivery_date.strftime('%Y-%m-%d')}."

        return CutoffValidationResponse(
            is_past_cutoff=is_past_cutoff,
            cutoff_time=cutoff_str,
            current_time=current_time_str,
            current_timezone="UTC",
            next_delivery_date=next_delivery_date,
            message=message
        )

    def validate_order(
        self,
        customer_id: int,
        items: List[Union[Dict[str, Any], PortalOrderLineCreate]],
        current_dt: Optional[datetime] = None,
        conn=None
    ) -> OrderValidationResponse:
        """Validate order rules: minimum order threshold, contracted item pricing, and cutoff status."""
        customer = self.portal_repo.get_customer_by_id(customer_id, conn=conn)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist.")

        errors: List[str] = []
        warnings: List[str] = []

        if not items:
            errors.append("Order must contain at least one line item.")
            items_dict = []
        else:
            items_dict = []
            for item in items:
                if isinstance(item, PortalOrderLineCreate):
                    items_dict.append(item.model_dump())
                elif isinstance(item, dict):
                    items_dict.append(item)
                else:
                    items_dict.append(dict(item))

        subtotal = 0.0
        if items_dict:
            try:
                resolved_lines = self.pricing_service.resolve_line_items_pricing(
                    customer_id=customer_id,
                    items=items_dict
                )
                subtotal = round(sum(line['line_total'] for line in resolved_lines), 2)
            except Exception as e:
                errors.append(str(e))

        min_order_amount = float(customer.get('min_order_amount', 0.0))
        meets_minimum = True
        if min_order_amount > 0 and subtotal < min_order_amount:
            meets_minimum = False
            errors.append(
                f"Order subtotal ${subtotal:.2f} is below the minimum required order amount of ${min_order_amount:.2f}."
            )

        cutoff_status = self.validate_cutoff_time(customer_id, current_dt=current_dt, conn=conn)
        if cutoff_status.is_past_cutoff:
            warnings.append(cutoff_status.message)

        is_valid = len(errors) == 0

        return OrderValidationResponse(
            is_valid=is_valid,
            subtotal=subtotal,
            min_order_amount=min_order_amount,
            meets_minimum=meets_minimum,
            cutoff_status=cutoff_status,
            errors=errors,
            warnings=warnings
        )

    def create_order(
        self,
        customer_id: int,
        order_in: PortalOrderCreate,
        user_id: Optional[int] = None,
        current_dt: Optional[datetime] = None,
        conn=None
    ) -> PortalOrderResponse:
        """Create a new replenishment sales order with contracted pricing, cutoff validation, and minimum threshold checks."""
        customer = self.portal_repo.get_customer_by_id(customer_id, conn=conn)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist.")
        if not customer.get('is_active', True):
            raise ValueError("Customer account is inactive.")

        if not order_in.items:
            raise ValueError("Order must contain at least one line item.")

        items_dict = [item.model_dump() for item in order_in.items]
        resolved_lines = self.pricing_service.resolve_line_items_pricing(
            customer_id=customer_id,
            items=items_dict
        )

        subtotal = round(sum(line['line_total'] for line in resolved_lines), 2)

        min_order_amount = float(customer.get('min_order_amount', 0.0))
        if min_order_amount > 0 and subtotal < min_order_amount:
            raise ValueError(
                f"Order subtotal ${subtotal:.2f} is below the minimum required order amount of ${min_order_amount:.2f}."
            )

        cutoff_status = self.validate_cutoff_time(customer_id, current_dt=current_dt, conn=conn)
        requested_delivery_date = order_in.requested_delivery_date or cutoff_status.next_delivery_date

        warehouse_id = order_in.warehouse_id
        if not warehouse_id:
            active_wh = self.portal_repo.get_active_warehouse(conn=conn)
            warehouse_id = active_wh['id'] if active_wh else None

        tax_rate_id = customer.get('default_tax_rate_id')
        tax_rate_record = self.portal_repo.get_tax_rate(tax_rate_id, conn=conn)
        tax_pct = float(tax_rate_record['rate']) if tax_rate_record else 0.0
        tax = round(subtotal * (tax_pct / 100.0), 2)
        grand_total = round(subtotal + tax, 2)

        status = order_in.status if order_in.status in ('Draft', 'Pending', 'Confirmed') else 'Confirmed'

        notes_parts = []
        if requested_delivery_date:
            notes_parts.append(f"[Delivery Date: {requested_delivery_date.strftime('%Y-%m-%d')}]")
        if order_in.notes:
            notes_parts.append(order_in.notes.strip())
        order_notes = "\n".join(notes_parts) if notes_parts else None

        order_data = {
            'customer_id': customer_id,
            'warehouse_id': warehouse_id,
            'subtotal': subtotal,
            'tax': tax,
            'grand_total': grand_total,
            'status': status,
            'order_date': (current_dt or datetime.now(timezone.utc)).date(),
            'notes': order_notes,
            'price_list_id': customer.get('default_price_list_id'),
            'tax_rate_id': tax_rate_id,
            'payment_term_id': customer.get('payment_term_id'),
            'created_by': user_id,
            'updated_by': user_id,
        }

        created = self.portal_repo.create_order(order_data, resolved_lines, conn=conn)

        lines_response = [
            PortalOrderLineResponse(
                id=line.get('id'),
                sales_order_id=created['id'],
                product_id=line.get('product_id'),
                product_code=line.get('product_code'),
                product_name=line.get('product_name', ''),
                uom_name=line.get('uom_name'),
                qty=line.get('qty', 0.0),
                unit_price=line.get('unit_price', 0.0),
                line_total=line.get('line_total', 0.0),
                line_number=line.get('line_number', 1)
            )
            for line in created.get('lines', [])
        ]

        return PortalOrderResponse(
            id=created['id'],
            order_number=created['order_number'],
            customer_id=created['customer_id'],
            customer_name=customer.get('name'),
            warehouse_id=created.get('warehouse_id'),
            subtotal=created['subtotal'],
            tax=created['tax'],
            grand_total=created['grand_total'],
            status=created['status'],
            order_date=created['order_date'],
            requested_delivery_date=requested_delivery_date,
            notes=created.get('notes'),
            lines=lines_response,
            created_at=created.get('created_at'),
            created_by=created.get('created_by'),
            updated_at=created.get('updated_at'),
            updated_by=created.get('updated_by'),
            update_number=created.get('update_number', 1)
        )

    def get_orders(
        self,
        customer_id: int,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
        conn=None
    ) -> Tuple[List[PortalOrderResponse], int]:
        """Fetch customer order history strictly isolated to customer_id."""
        orders_raw, total = self.portal_repo.get_orders(
            customer_id=customer_id,
            status=status,
            page=page,
            limit=limit,
            conn=conn
        )

        orders: List[PortalOrderResponse] = []
        for o in orders_raw:
            lines = [
                PortalOrderLineResponse(
                    id=l.get('id'),
                    sales_order_id=o['id'],
                    product_id=l.get('product_id'),
                    product_code=l.get('product_code'),
                    product_name=l.get('product_name', ''),
                    uom_name=l.get('uom_name'),
                    qty=l.get('qty', 0.0),
                    unit_price=l.get('unit_price', 0.0),
                    line_total=l.get('line_total', 0.0),
                    line_number=l.get('line_number', 1)
                )
                for l in o.get('lines', [])
            ]

            orders.append(
                PortalOrderResponse(
                    id=o['id'],
                    order_number=o['order_number'],
                    customer_id=o['customer_id'],
                    customer_name=o.get('customer_name'),
                    warehouse_id=o.get('warehouse_id'),
                    subtotal=o['subtotal'],
                    tax=o['tax'],
                    grand_total=o['grand_total'],
                    status=o['status'],
                    order_date=o['order_date'],
                    notes=o.get('notes'),
                    lines=lines,
                    created_at=o.get('created_at'),
                    created_by=o.get('created_by'),
                    updated_at=o.get('updated_at'),
                    updated_by=o.get('updated_by'),
                    update_number=o.get('update_number', 1)
                )
            )

        return orders, total

    def get_order_by_id(
        self,
        customer_id: int,
        order_id: int,
        conn=None
    ) -> Optional[PortalOrderResponse]:
        """Retrieve single customer order with full line breakdown, scoped strictly to customer_id."""
        order_raw = self.portal_repo.get_order_by_id(order_id=order_id, customer_id=customer_id, conn=conn)
        if not order_raw:
            return None

        lines = [
            PortalOrderLineResponse(
                id=l.get('id'),
                sales_order_id=order_raw['id'],
                product_id=l.get('product_id'),
                product_code=l.get('product_code'),
                product_name=l.get('product_name', ''),
                uom_name=l.get('uom_name'),
                qty=l.get('qty', 0.0),
                unit_price=l.get('unit_price', 0.0),
                line_total=l.get('line_total', 0.0),
                line_number=l.get('line_number', 1)
            )
            for l in order_raw.get('lines', [])
        ]

        return PortalOrderResponse(
            id=order_raw['id'],
            order_number=order_raw['order_number'],
            customer_id=order_raw['customer_id'],
            customer_name=order_raw.get('customer_name'),
            warehouse_id=order_raw.get('warehouse_id'),
            subtotal=order_raw['subtotal'],
            tax=order_raw['tax'],
            grand_total=order_raw['grand_total'],
            status=order_raw['status'],
            order_date=order_raw['order_date'],
            notes=order_raw.get('notes'),
            lines=lines,
            created_at=order_raw.get('created_at'),
            created_by=order_raw.get('created_by'),
            updated_at=order_raw.get('updated_at'),
            updated_by=order_raw.get('updated_by'),
            update_number=order_raw.get('update_number', 1)
        )

    def reorder(
        self,
        customer_id: int,
        reorder_in: PortalReorderRequest,
        user_id: Optional[int] = None,
        current_dt: Optional[datetime] = None,
        conn=None
    ) -> PortalOrderResponse:
        """1-Click Replenishment Reorder from order history, recalculating totals using current contracted pricing."""
        customer = self.portal_repo.get_customer_by_id(customer_id, conn=conn)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist.")
        if not customer.get('allow_reorders', True):
            raise ValueError("1-Click reordering is disabled for this customer account.")

        prev_order = self.portal_repo.get_order_by_id(
            order_id=reorder_in.order_id,
            customer_id=customer_id,
            conn=conn
        )
        if not prev_order:
            raise ValueError(f"Previous order #{reorder_in.order_id} not found.")

        prev_lines = prev_order.get('lines', [])
        if not prev_lines:
            raise ValueError(f"Previous order #{reorder_in.order_id} contains no line items to reorder.")

        items: List[PortalOrderLineCreate] = []
        for line in prev_lines:
            pid = line.get('product_id')
            qty = float(line.get('qty', 0))
            if pid and qty > 0:
                items.append(PortalOrderLineCreate(product_id=pid, qty=qty))

        if not items:
            raise ValueError("No valid products found in previous order to reorder.")

        reorder_notes = reorder_in.notes or f"Replenishment reorder based on #{prev_order.get('order_number')}"
        order_create = PortalOrderCreate(
            items=items,
            warehouse_id=prev_order.get('warehouse_id'),
            requested_delivery_date=reorder_in.requested_delivery_date,
            notes=reorder_notes,
            status=reorder_in.status
        )

        return self.create_order(
            customer_id=customer_id,
            order_in=order_create,
            user_id=user_id,
            current_dt=current_dt,
            conn=conn
        )

    def cancel_order(
        self,
        customer_id: int,
        order_id: int,
        cancel_in: Optional[PortalOrderCancelRequest] = None,
        user_id: Optional[int] = None,
        conn=None
    ) -> PortalOrderResponse:
        """Cancel an unfulfilled customer order (Draft, Pending, Confirmed)."""
        order = self.portal_repo.get_order_by_id(order_id=order_id, customer_id=customer_id, conn=conn)
        if not order:
            raise ValueError(f"Order #{order_id} not found.")

        current_status = order.get('status')
        if current_status not in ('Draft', 'Pending', 'Confirmed'):
            raise ValueError(f"Cannot cancel order in '{current_status}' status.")

        reason_text = cancel_in.reason.strip() if cancel_in and cancel_in.reason else None
        current_notes = order.get('notes') or ''
        if reason_text:
            updated_notes = f"{current_notes}\n[Cancelled by customer: {reason_text}]".strip()
        else:
            updated_notes = f"{current_notes}\n[Cancelled by customer]".strip()

        updated = self.portal_repo.update_order_status(
            order_id=order_id,
            status='Cancelled',
            notes=updated_notes,
            customer_id=customer_id,
            conn=conn
        )
        if not updated:
            raise RuntimeError(f"Failed to cancel order #{order_id}.")

        return self.get_order_by_id(customer_id=customer_id, order_id=order_id, conn=conn)
