from decimal import Decimal
import logging
from typing import Optional
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.context import get_current_tenant
from modules.sales.services.credit_service import CreditService
from modules.administration.services.notification_service import NotificationService
from packages.database.connection import get_connection, release_connection

logger = logging.getLogger(__name__)


def _to_decimal(value) -> Decimal:
    """Coerce a numeric input to Decimal without raising on mixed operand types."""
    try:
        return Decimal(str(value))
    except (TypeError, ValueError, ArithmeticError):
        return Decimal(0)


class EnhancedSalesOrderService(CrudService):
    def __init__(
        self,
        repo: Optional[CrudRepository] = None,
        line_repo: Optional[CrudRepository] = None,
        price_list_item_repo: Optional[CrudRepository] = None,
        tax_rate_repo: Optional[CrudRepository] = None,
        customer_repo: Optional[CrudRepository] = None,
        inv_repo: Optional[CrudRepository] = None,
        credit_service: Optional[CreditService] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        order_repo = repo or CrudRepository(
            'T0012',
            business_columns=[
                'id',
                'order_number',
                'customer_id',
                'warehouse_id',
                'subtotal',
                'tax',
                'grand_total',
                'freight_amount',
                'discount_amount',
                'sales_rep_id',
                'status',
                'order_date',
                'notes',
                'price_list_id',
                'tax_rate_id',
                'payment_term_id',
                'client_order_uuid',
                'is_offline_sync',
                'sync_status',
                'offline_created_at',
                'hold_reason',
                'hold_released_by',
                'hold_released_at',
                'hold_release_reason',
            ],
        )
        super().__init__(order_repo)
        self.line_repo = line_repo or CrudRepository(
            'T0013',
            business_columns=[
                'id',
                'sales_order_id',
                'product_id',
                'product_name',
                'uom_id',
                'qty',
                'unit_price',
                'cost_price',
                'discount',
                'line_total',
                'line_number',
                'is_catch_weight',
                'pricing_uom_id',
                'unit_price_pricing_uom',
                'nominal_weight',
                'catch_weight_actual',
                'recalculated_total',
            ],
        )
        self.price_list_item_repo = price_list_item_repo or CrudRepository(
            'T0084', business_columns=['id', 'price_list_id', 'product_id', 'unit_price', 'min_qty']
        )
        self.tax_rate_repo = tax_rate_repo or CrudRepository(
            'T0085', business_columns=['id', 'name', 'code', 'rate', 'type']
        )
        self.customer_repo = customer_repo or CrudRepository(
            'T0010', business_columns=['id', 'name', 'credit_limit', 'balance']
        )
        self.inv_repo = inv_repo or CrudRepository(
            'T0090',
            business_columns=[
                'id',
                'invoice_number',
                'invoice_type',
                'partner_id',
                'sales_order_id',
                'sales_rep_id',
                'issue_date',
                'due_date',
                'total_amount',
                'freight_amount',
                'discount_amount',
                'status',
                'notes',
            ],
        )
        self.credit_service = credit_service or CreditService(
            customer_repo=self.customer_repo,
            invoice_repo=self.inv_repo,
            order_repo=self.repo,
        )
        self.notification_service = notification_service or NotificationService()

    def _notify_credit_hold(
        self,
        order: dict,
        hold_reason: str,
        customer_name: str = None,
        conn=None,
    ):
        """Dispatch instant manager notifications and WebSocket broadcast when an order is placed on Credit Hold."""
        if not order:
            return
        order_id = order.get('id')
        order_number = order.get('order_number') or str(order_id)
        if not customer_name:
            customer_id = order.get('customer_id')
            if customer_id and self.customer_repo:
                try:
                    cust = self.customer_repo.get(customer_id, conn=conn)
                    customer_name = cust.get('name') if cust else f"Customer #{customer_id}"
                except Exception as e:
                    logger.warning(f"Failed to fetch customer for credit hold notification: {e}")
                    customer_name = f"Customer #{customer_id}"
            else:
                customer_name = "Customer"

        # 1. Send in-app notifications to financial managers & credit controllers
        if self.notification_service:
            try:
                title = f"Credit Hold: Sales Order #{order_number}"
                msg = (
                    f"Sales Order #{order_number} for customer {customer_name} has been placed on Credit Hold. "
                    f"Reason: {hold_reason}"
                )
                self.notification_service.notify_roles(
                    roles=['admin', 'financial_manager', 'finance', 'manager', 'credit_controller', 'accounting'],
                    title=title,
                    message=msg,
                    notification_type='Credit Hold',
                    reference_type='SalesOrder',
                    reference_id=order_id,
                    conn=conn,
                )
                logger.info(f"Dispatched credit hold notification for order #{order_number} (id: {order_id})")
            except Exception as e:
                logger.warning(f"Failed to dispatch credit hold notification for order {order_id}: {e}")

        # 2. Trigger WebSocket broadcast
        try:
            business_id = get_current_tenant() or order.get('business_id') or 1
            self._dispatch_ws_broadcast(
                business_id=business_id,
                order_id=order_id,
                order_number=order_number,
                status='Credit Hold',
                hold_reason=hold_reason,
                customer_name=customer_name,
                customer_id=order.get('customer_id'),
                grand_total=float(order.get('grand_total', 0) or 0),
            )
        except Exception as e:
            logger.warning(f"Failed to trigger credit hold WebSocket broadcast for order {order_id}: {e}")

    def _dispatch_ws_broadcast(
        self,
        business_id: int,
        order_id: int,
        order_number: str,
        status: str,
        hold_reason: str = None,
        customer_name: str = None,
        customer_id: int = None,
        grand_total: float = None,
    ):
        """Dispatch WebSocket broadcast safely across sync and async contexts."""
        try:
            import asyncio
            from packages.ws.broadcast import order_status_changed, order_credit_hold_placed

            async def _do_broadcast():
                try:
                    await order_status_changed(
                        business_id,
                        order_id,
                        order_number,
                        status,
                        hold_reason=hold_reason,
                        customer_name=customer_name,
                    )
                    if status == 'Credit Hold':
                        await order_credit_hold_placed(
                            business_id=business_id,
                            order_id=order_id,
                            order_number=order_number,
                            customer_id=customer_id,
                            customer_name=customer_name,
                            hold_reason=hold_reason,
                            grand_total=grand_total,
                        )
                except Exception as b_err:
                    logger.warning(f"Error during websocket broadcast execution: {b_err}")

            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    loop.create_task(_do_broadcast())
                else:
                    loop.run_until_complete(_do_broadcast())
            except RuntimeError:
                try:
                    asyncio.run(_do_broadcast())
                except Exception as sync_err:
                    logger.warning(f"Failed to execute websocket broadcast on fresh event loop: {sync_err}")
        except Exception as e:
            logger.warning(f"Failed to dispatch websocket broadcast: {e}")

    def create(self, payload: dict, conn=None):
        payload = dict(payload)
        if not payload.get('grand_total') and payload.get('subtotal') is not None:
            payload['grand_total'] = payload.get('subtotal', 0) + payload.get('tax', 0)
        customer_id = payload.get('customer_id')
        is_hold = False
        eval_result = None
        if customer_id and self.credit_service:
            order_amount = float(payload.get('grand_total', 0) or 0)
            eval_result = self.credit_service.evaluate_order_credit(
                customer_id=customer_id,
                order_amount=order_amount,
                conn=conn,
            )
            if eval_result.get('is_hold_required'):
                payload['status'] = 'Credit Hold'
                payload['hold_reason'] = eval_result.get('hold_reason')
                is_hold = True
                logger.warning(
                    f"EnhancedSalesOrderService: Order placed on Credit Hold for customer {eval_result.get('customer_name')} "
                    f"(id {customer_id}): {eval_result.get('hold_reason')}"
                )
            elif not payload.get('status'):
                payload['status'] = 'Pending'
        elif not payload.get('status'):
            payload['status'] = 'Pending'
        
        created = super().create(payload, conn=conn)
        if is_hold and created:
            self._notify_credit_hold(
                created,
                hold_reason=eval_result.get('hold_reason', '') if eval_result else payload.get('hold_reason', ''),
                customer_name=eval_result.get('customer_name') if eval_result else None,
                conn=conn,
            )
        return created

    def create_with_lines(self, order_data, lines, conn=None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            order_payload = dict(order_data)
            order = super().create(order_payload, conn=conn)
            subtotal = Decimal(0)
            tax_rate_pct = _to_decimal(self._lookup_tax_rate(order_payload.get('tax_rate_id'), conn=conn))
            price_list_id = order_payload.get('price_list_id')

            for line_data in lines:
                unit_price = _to_decimal(self._resolve_unit_price(line_data, price_list_id, conn=conn))
                qty = _to_decimal(line_data.get('qty', 1))
                line_total = qty * unit_price
                subtotal += line_total
                self.line_repo.create({
                    'sales_order_id': order['id'],
                    'product_id': line_data.get('product_id'),
                    'product_name': line_data.get('product_name', ''),
                    'qty': float(qty),
                    'unit_price': float(unit_price),
                    'line_total': float(line_total),
                    'line_number': line_data.get('line_number', 1),
                    'is_catch_weight': line_data.get('is_catch_weight', False),
                    'pricing_uom_id': line_data.get('pricing_uom_id'),
                    'unit_price_pricing_uom': line_data.get('unit_price_pricing_uom'),
                    'nominal_weight': line_data.get('nominal_weight'),
                    'catch_weight_actual': line_data.get('catch_weight_actual'),
                    'recalculated_total': line_data.get('recalculated_total'),
                }, conn=conn)

            tax_amount = subtotal * tax_rate_pct / Decimal(100)
            grand_total = subtotal + tax_amount

            update_payload = {
                'subtotal': float(subtotal),
                'tax': float(tax_amount),
                'grand_total': float(grand_total),
            }

            customer_id = order_payload.get('customer_id')
            is_hold = False
            eval_result = None
            if customer_id and self.credit_service:
                eval_result = self.credit_service.evaluate_order_credit(
                    customer_id=customer_id,
                    order_amount=float(grand_total),
                    conn=conn,
                )
                if eval_result.get('is_hold_required'):
                    update_payload['status'] = 'Credit Hold'
                    update_payload['hold_reason'] = eval_result.get('hold_reason')
                    is_hold = True
                    logger.warning(
                        f"EnhancedSalesOrderService.create_with_lines: Order {order['id']} placed on Credit Hold: "
                        f"{eval_result.get('hold_reason')}"
                    )
                elif order_payload.get('status'):
                    update_payload['status'] = order_payload.get('status')
                else:
                    update_payload['status'] = order.get('status') or 'Pending'
            elif order_payload.get('status'):
                update_payload['status'] = order_payload.get('status')
            else:
                update_payload['status'] = order.get('status') or 'Pending'

            result = super().update(order['id'], update_payload, conn=conn)
            if is_hold and result:
                self._notify_credit_hold(
                    result,
                    hold_reason=eval_result.get('hold_reason', '') if eval_result else update_payload.get('hold_reason', ''),
                    customer_name=eval_result.get('customer_name') if eval_result else None,
                    conn=conn,
                )
            if should_release:
                conn.commit()
            return result
        except Exception:
            if should_release:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if should_release:
                release_connection(conn)

    def _lookup_tax_rate(self, tax_rate_id, conn=None):
        if not tax_rate_id:
            return 0
        tax_rate = self.tax_rate_repo.get(tax_rate_id, conn=conn)
        return tax_rate.get('rate', 0) if tax_rate else 0

    def _resolve_unit_price(self, line_data, price_list_id, conn=None):
        unit_price = line_data.get('unit_price', 0)
        if unit_price and unit_price > 0:
            return unit_price
        product_id = line_data.get('product_id')
        if not price_list_id or not product_id:
            return 0
        prices = self.price_list_item_repo.list(filters={
            'price_list_id': price_list_id,
            'product_id': product_id,
        }, conn=conn)
        return prices[0].get('unit_price', 0) if prices else 0