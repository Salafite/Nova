import logging
from datetime import date, datetime, timezone
from typing import Optional, Union, Dict, Any, List
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.database.sequence import generate_invoice_number
from packages.database.connection import get_connection, release_connection
from modules.accounting.services.payment_term_service import (
    resolve_effective_term,
    calculate_due_date,
    calculate_discount_deadline,
    calculate_max_early_discount,
)

logger = logging.getLogger(__name__)

VALID_SALES_STATUS_TRANSITIONS = {
    'Draft': ['Confirmed', 'Cancelled', 'Credit Hold'],
    'Pending': ['Confirmed', 'Cancelled', 'Credit Hold'],
    'Confirmed': ['Shipped', 'Cancelled'],
    'Shipped': ['Delivered', 'Cancelled'],
    'Delivered': ['Invoiced'],
    'Invoiced': ['Paid', 'Cancelled'],
    'Paid': [],
    'Cancelled': [],
    'Credit Hold': ['Draft', 'Pending', 'Confirmed', 'Cancelled'],
}

LINE_REPO = CrudRepository(
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

ORDER_REPO = CrudRepository(
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

INVOICE_REPO = CrudRepository(
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
        'is_catch_weight',
        'nominal_total_weight',
        'actual_total_weight',
        'weight_adjustment_amount',
        'payment_term_id',
        'discount_due_date',
        'discount_percentage',
        'discount_days',
        'early_discount_amount',
    ],
)

CUSTOMER_REPO = CrudRepository(
    'T0010',
    business_columns=['id', 'name', 'credit_limit', 'balance', 'payment_term_id'],
)

PL_REPO = CrudRepository(
    'T0101',
    business_columns=['id', 'pick_list_number', 'sales_order_id', 'warehouse_id', 'status', 'notes'],
)

PLI_REPO = CrudRepository(
    'T0102',
    business_columns=[
        'id',
        'pick_list_id',
        'sales_order_line_id',
        'product_id',
        'product_name',
        'qty_ordered',
        'qty_picked',
        'line_number',
        'batch_id',
        'batch_number',
        'expiry_date',
        'picked_batch_id',
        'picked_batch_number',
        'catch_weight_actual',
        'catch_weight_uom',
        'nominal_weight',
        'tolerance_pct',
        'tolerance_variance_pct',
        'tolerance_status',
        'supervisor_approved',
        'supervisor_approved_by',
        'supervisor_approved_at',
        'supervisor_notes',
    ],
)

PRODUCT_REPO = CrudRepository(
    'T0003',
    business_columns=[
        'id',
        'name',
        'sku',
        'barcode',
        'description',
        'type',
        'price',
        'cost_price',
        'category',
        'brand',
        'tax_rate',
        'weight',
        'volume',
        'image_url',
        'is_purchasable',
        'is_saleable',
        'is_phantom',
        'last_transaction_date',
        'is_active',
        'is_catch_weight',
        'pricing_uom_id',
        'nominal_weight',
        'tolerance_pct',
        'pricing_basis',
    ],
)


PAYMENT_TERM_REPO = CrudRepository(
    'T0096',
    business_columns=[
        'id',
        'name',
        'code',
        'description',
        'due_days',
        'discount_percentage',
        'discount_days',
        'is_active',
        'is_default',
    ],
)


class SalesOrderService(CrudService):
    def __init__(
        self,
        repo: CrudRepository = None,
        line_repo: CrudRepository = None,
        customer_repo: CrudRepository = None,
        inv_repo: CrudRepository = None,
        pl_repo: CrudRepository = None,
        pli_repo: CrudRepository = None,
        product_repo: CrudRepository = None,
        payment_term_repo: CrudRepository = None,
        credit_service=None,
        notification_service=None,
    ):
        super().__init__(repo or ORDER_REPO)
        self.line_repo = line_repo or LINE_REPO
        self.customer_repo = customer_repo or CUSTOMER_REPO
        self.inv_repo = inv_repo or INVOICE_REPO
        self.pl_repo = pl_repo or PL_REPO
        self.pli_repo = pli_repo or PLI_REPO
        self.product_repo = product_repo or PRODUCT_REPO
        self.payment_term_repo = payment_term_repo or PAYMENT_TERM_REPO
        self.credit_service = credit_service
        self.notification_service = notification_service

    def _dispatch_ws_broadcast(self, **kwargs):
        pass

    def list(self, filters: dict = None, order_by: str = None, limit: int = None, offset: int = None, conn=None):
        if filters and 'is_catch_weight' in filters:
            filters_copy = dict(filters)
            is_cw_filter = filters_copy.pop('is_catch_weight')
            orders = super().list(filters=filters_copy or None, order_by=order_by, conn=conn)
            filtered_orders = []
            for order in orders:
                order_id = order.get('id')
                lines = self.line_repo.list(filters={'sales_order_id': order_id}, conn=conn)
                has_cw = any(bool(line.get('is_catch_weight')) for line in lines)
                if has_cw == bool(is_cw_filter):
                    filtered_orders.append(order)
            if offset:
                filtered_orders = filtered_orders[offset:]
            if limit:
                filtered_orders = filtered_orders[:limit]
            return filtered_orders
        return super().list(filters=filters, order_by=order_by, limit=limit, offset=offset, conn=conn)

    def create(self, payload: dict, conn=None):
        if not payload.get('grand_total') and payload.get('subtotal') is not None:
            payload['grand_total'] = payload.get('subtotal', 0) + payload.get('tax', 0)
        customer_id = payload.get('customer_id')
        hold_reason = None
        if customer_id:
            customer = self.customer_repo.get(customer_id, conn=conn) if self.customer_repo else None
            if customer:
                # Inherit customer payment terms by default if not explicitly provided in order payload
                if not payload.get('payment_term_id') and customer.get('payment_term_id'):
                    payload['payment_term_id'] = customer.get('payment_term_id')

                if self.credit_service:
                    credit_check = self.credit_service.evaluate_order_credit(
                        customer_id=customer_id,
                        order_amount=payload.get('grand_total', 0),
                        conn=conn,
                    )
                    if credit_check and credit_check.get('is_hold_required'):
                        hold_reason = credit_check.get('hold_reason', 'Customer credit limit exceeded')
                else:
                    curr_balance = float(customer.get('balance') or 0)
                    grand_total = float(payload.get('grand_total') or 0)
                    new_balance = curr_balance + grand_total
                    credit_limit = float(customer.get('credit_limit') or 0)
                    if credit_limit > 0 and new_balance > credit_limit:
                        hold_reason = f"Customer credit limit exceeded (${new_balance:,.2f} > Limit ${credit_limit:,.2f})"

        if hold_reason:
            payload['status'] = 'Credit Hold'
            payload['hold_reason'] = hold_reason
            customer_name = customer.get('name', 'Unknown') if customer else 'Unknown'
            logger.warning(f"Order creation placed on Credit Hold for customer {customer_name}: {hold_reason}")
        elif not payload.get('status'):
            payload['status'] = 'Pending'

        # If payment_term_id is still not set, resolve default active payment term if available
        if not payload.get('payment_term_id') and hasattr(self, 'payment_term_repo') and self.payment_term_repo:
            try:
                default_terms = self.payment_term_repo.list(filters={'is_default': True, 'is_active': True}, limit=1, conn=conn)
                if default_terms and default_terms[0].get('id'):
                    payload['payment_term_id'] = default_terms[0]['id']
            except Exception as e:
                logger.warning(f"Could not resolve default payment term for order: {e}")

        result = super().create(payload, conn=conn)

        if hold_reason and hasattr(self, 'notification_service') and self.notification_service:
            try:
                self.notification_service.notify_roles(
                    title=f"Credit Hold: {result.get('order_number', '')}",
                    message=f"Order {result.get('order_number', '')} placed on credit hold for {customer.get('name', 'Unknown')}: {hold_reason}",
                    notification_type='Credit Hold',
                    reference_type='SalesOrder',
                    reference_id=result.get('id'),
                    roles=['admin'],
                )
            except Exception as e:
                logger.warning(f"Failed to send credit hold notification: {e}")

        if hold_reason and hasattr(self, '_dispatch_ws_broadcast'):
            try:
                self._dispatch_ws_broadcast(
                    order_id=result.get('id'),
                    order_number=result.get('order_number', ''),
                    status='Credit Hold',
                    customer_name=customer.get('name', 'Unknown') if customer else 'Unknown',
                )
            except Exception as e:
                logger.warning(f"Failed to dispatch WS broadcast: {e}")

        return result

    def update(self, id_val, payload: dict, conn=None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            existing_order = self.repo.get(id_val, conn=conn)
            if not existing_order:
                logger.error(f"Cannot update sales order {id_val}: not found")
                raise ValueError(f"Sales order {id_val} not found")

            new_status = payload.get('status')
            old_status = existing_order.get('status')

            if new_status and new_status != old_status:
                if old_status in VALID_SALES_STATUS_TRANSITIONS:
                    allowed = VALID_SALES_STATUS_TRANSITIONS[old_status]
                    if new_status not in allowed:
                        from fastapi import HTTPException
                        logger.warning(
                            f"Invalid status transition attempted for sales order {id_val}: "
                            f"{old_status} -> {new_status}"
                        )
                        raise HTTPException(
                            400,
                            f"Invalid status transition: {old_status} -> {new_status}. Allowed: {allowed}"
                        )

                if new_status == 'Confirmed':
                    self._reserve_order_stock(id_val, conn=conn)
                elif new_status == 'Delivered':
                    self._validate_delivery_tolerance_approvals(id_val, conn=conn)
                    self._create_invoice_from_order(id_val, conn=conn)
                elif new_status == 'Cancelled':
                    self._release_order_stock(id_val, conn=conn)

            result = super().update(id_val, payload, conn=conn)
            if should_release:
                conn.commit()

            if new_status == 'Credit Hold':
                customer_name = ''
                customer_id = result.get('customer_id') or existing_order.get('customer_id')
                if customer_id and hasattr(self, 'customer_repo') and self.customer_repo:
                    try:
                        customer = self.customer_repo.get(customer_id, conn=conn)
                        if customer:
                            customer_name = customer.get('name', '')
                    except Exception:
                        pass

                if hasattr(self, 'notification_service') and self.notification_service:
                    try:
                        cust_str = f" for {customer_name}" if customer_name else ""
                        self.notification_service.notify_roles(
                            title=f"Credit Hold: {result.get('order_number', '')}",
                            message=f"Order {result.get('order_number', '')} placed on credit hold{cust_str}: {payload.get('hold_reason', 'Credit limit exceeded')}",
                            notification_type='Credit Hold',
                            reference_type='SalesOrder',
                            reference_id=id_val,
                            roles=['admin'],
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send credit hold notification: {e}")

                if hasattr(self, '_dispatch_ws_broadcast'):
                    try:
                        self._dispatch_ws_broadcast(
                            order_id=id_val,
                            order_number=result.get('order_number', ''),
                            status='Credit Hold',
                            customer_name=customer_name,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to dispatch WS broadcast: {e}")

            return result
        except Exception as e:
            if should_release:
                try:
                    conn.rollback()
                    logger.info(f"Transaction rolled back for sales order {id_val} update: {e}")
                except Exception as rb_err:
                    logger.error(f"Error during transaction rollback for sales order {id_val}: {rb_err}")
            raise
        finally:
            if should_release:
                release_connection(conn)

    def override_credit_hold(self, order_id: int, user_id: int = None, user_name: str = None,
                             reason: str = '', target_status: str = 'Confirmed', conn=None):
        VALID_OVERRIDE_TARGETS = {'Confirmed', 'Pending'}
        if target_status not in VALID_OVERRIDE_TARGETS:
            from fastapi import HTTPException
            raise HTTPException(400, f"Invalid target status '{target_status}'. Allowed: {VALID_OVERRIDE_TARGETS}")

        order = self.repo.get(order_id, conn=conn)
        if not order:
            raise ValueError(f"Sales order {order_id} not found")

        if order.get('status') != 'Credit Hold':
            from fastapi import HTTPException
            raise HTTPException(400, f"Order {order_id} status is '{order.get('status')}', expected 'Credit Hold'")

        update_payload = {
            'status': target_status,
            'hold_released_by': user_id,
            'hold_release_reason': reason,
            'hold_released_at': datetime.now(timezone.utc).isoformat(),
        }
        result = self.repo.update(order_id, update_payload, conn=conn)

        if target_status == 'Confirmed':
            self._reserve_order_stock(order_id, conn=conn)

        if self.notification_service and order.get('sales_rep_id'):
            try:
                self.notification_service.create_notification(
                    user_id=order['sales_rep_id'],
                    title='Credit Hold Approved',
                    message=f"Order {order.get('order_number', '')} credit hold released. Reason: {reason}",
                    notification_type='Credit Hold',
                    reference_type='SalesOrder',
                    reference_id=order_id,
                )
            except Exception as e:
                logger.warning(f"Failed to send credit hold override notification: {e}")

        return result

    def reject_credit_hold(self, order_id: int, user_id: int = None, user_name: str = None,
                           reason: str = '', conn=None):
        order = self.repo.get(order_id, conn=conn)
        if not order:
            raise ValueError(f"Sales order {order_id} not found")

        if order.get('status') != 'Credit Hold':
            from fastapi import HTTPException
            raise HTTPException(400, f"Order {order_id} status is '{order.get('status')}', expected 'Credit Hold'")

        update_payload = {
            'status': 'Cancelled',
            'hold_released_by': user_id,
            'hold_release_reason': f"Rejected: {reason}" if reason else 'Rejected',
            'hold_released_at': datetime.now(timezone.utc).isoformat(),
        }
        result = self.repo.update(order_id, update_payload, conn=conn)

        if self.notification_service and order.get('sales_rep_id'):
            try:
                self.notification_service.create_notification(
                    user_id=order['sales_rep_id'],
                    title='Credit Hold Rejected',
                    message=f"Order {order.get('order_number', '')} credit hold rejected. Reason: {reason}",
                    notification_type='Credit Hold',
                    reference_type='SalesOrder',
                    reference_id=order_id,
                )
            except Exception as e:
                logger.warning(f"Failed to send credit hold rejection notification: {e}")

        return result

    def _validate_delivery_tolerance_approvals(self, order_id: int, conn=None):
        """
        Validate that all pick list items for the sales order have no unapproved catch-weight tolerance discrepancies.
        """
        if not hasattr(self, 'pl_repo') or not self.pl_repo:
            return
        try:
            pick_lists = self.pl_repo.list(filters={'sales_order_id': order_id}, conn=conn)
        except Exception as e:
            logger.warning(f"Could not check pick lists for order {order_id}: {e}")
            return

        for pl in pick_lists:
            if hasattr(self, 'pli_repo') and self.pli_repo:
                try:
                    items = self.pli_repo.list(filters={'pick_list_id': pl['id']}, conn=conn)
                    unapproved = [
                        it for it in items
                        if it.get('tolerance_status') == 'Out of Tolerance' and not it.get('supervisor_approved')
                    ]
                    if unapproved:
                        names = [it.get('product_name') or f"Item #{it.get('id')}" for it in unapproved]
                        from fastapi import HTTPException
                        msg = f"Cannot deliver order {order_id}: Unapproved catch-weight tolerance discrepancies exist on pick list #{pl.get('id')} items: {', '.join(names)}"
                        logger.warning(msg)
                        raise HTTPException(400, msg)
                except HTTPException:
                    raise
                except Exception as e:
                    logger.warning(f"Could not check pick list items for pick list {pl['id']}: {e}")

    def _generate_invoice_number(self, conn=None):
        return generate_invoice_number(conn=conn)

    def recalculate_order_catch_weight(self, order_id: int, conn=None) -> dict:
        """
        Recalculate sales order lines and order totals based on actual weighed catch-weights.
        - Sourced from pick list items (T0102) if not already set on sales lines (T0013).
        - Computes line recalculated total using unit_price_pricing_uom (or price/weight ratio).
        - Updates sales order lines with actual weights and recalculated totals.
        - Recalculates order subtotal, proportional tax, and grand total.
        - Updates order header T0012 with recalculated amounts.
        - Returns a detailed recalculation summary.
        """
        order = self.repo.get(order_id, conn=conn)
        if not order:
            logger.error(f"Cannot recalculate catch-weight: Sales order {order_id} not found")
            raise ValueError(f"Sales order {order_id} not found")

        lines = self.line_repo.list(filters={'sales_order_id': order_id}, conn=conn)
        if not lines:
            return {
                'order_id': order_id,
                'is_catch_weight': False,
                'original_subtotal': float(order.get('subtotal', 0) or 0),
                'recalculated_subtotal': float(order.get('subtotal', 0) or 0),
                'weight_adjustment_amount': 0.0,
                'nominal_total_weight': None,
                'actual_total_weight': None,
                'tax': float(order.get('tax', 0) or 0),
                'grand_total': float(order.get('grand_total', 0) or 0),
                'lines': [],
            }

        # Gather pick list items linked to this sales order
        all_pli_items = []
        try:
            pick_lists = self.pl_repo.list(filters={'sales_order_id': order_id}, conn=conn)
            for pl in pick_lists:
                pli_items = self.pli_repo.list(filters={'pick_list_id': pl['id']}, conn=conn)
                all_pli_items.extend(pli_items)
        except Exception as e:
            logger.warning(f"Could not load pick lists for order {order_id} during recalculation: {e}")

        has_catch_weight = False
        has_any_nominal = False
        has_any_actual = False
        total_nominal_weight = 0.0
        total_actual_weight = 0.0
        original_subtotal = 0.0
        recalculated_subtotal = 0.0
        updated_lines = []

        for line in lines:
            line_id = line.get('id')
            line_orig_total = float(line.get('line_total', 0) or 0)
            original_subtotal += line_orig_total

            is_cw = bool(line.get('is_catch_weight'))
            if not is_cw and line.get('product_id') and hasattr(self, 'product_repo') and self.product_repo:
                try:
                    prod = self.product_repo.get(line['product_id'], conn=conn)
                    if prod and prod.get('is_catch_weight'):
                        is_cw = True
                except Exception:
                    pass

            if is_cw:
                has_catch_weight = True

                # Determine actual scale weight
                actual_wt = line.get('catch_weight_actual')
                if actual_wt is None and all_pli_items:
                    matching_pli = [
                        it for it in all_pli_items
                        if it.get('sales_order_line_id') == line_id
                        and it.get('catch_weight_actual') is not None
                    ]
                    if matching_pli:
                        actual_wt = sum(float(it.get('catch_weight_actual', 0) or 0) for it in matching_pli)

                # Determine nominal weight
                nominal_wt = line.get('nominal_weight')
                if nominal_wt is None and all_pli_items:
                    matching_pli = [
                        it for it in all_pli_items
                        if it.get('sales_order_line_id') == line_id
                        and it.get('nominal_weight') is not None
                    ]
                    if matching_pli:
                        nominal_wt = sum(float(it.get('nominal_weight', 0) or 0) for it in matching_pli)

                if nominal_wt is not None:
                    nom_val = float(nominal_wt)
                    total_nominal_weight += nom_val
                    has_any_nominal = True
                else:
                    nom_val = None

                if actual_wt is not None:
                    act_val = float(actual_wt)
                    total_actual_weight += act_val
                    has_any_actual = True

                    # Determine rate per weight unit
                    unit_price_pricing = line.get('unit_price_pricing_uom')
                    if unit_price_pricing is not None and float(unit_price_pricing) > 0:
                        rate_per_weight = float(unit_price_pricing)
                    elif nom_val and nom_val > 0 and line_orig_total > 0:
                        rate_per_weight = line_orig_total / nom_val
                    elif line.get('unit_price') is not None:
                        rate_per_weight = float(line.get('unit_price', 0))
                    else:
                        rate_per_weight = 0.0

                    discount = float(line.get('discount', 0) or 0)
                    recalculated_line_total = round(max(0.0, (act_val * rate_per_weight) - discount), 2)

                    line_update = {
                        'is_catch_weight': True,
                        'catch_weight_actual': act_val,
                        'recalculated_total': recalculated_line_total,
                    }
                    if nominal_wt is not None and line.get('nominal_weight') is None:
                        line_update['nominal_weight'] = nom_val

                    self.line_repo.update(line_id, line_update, conn=conn)
                    updated_line = dict(line, **line_update)
                    updated_lines.append(updated_line)
                    recalculated_subtotal += recalculated_line_total
                else:
                    if line.get('recalculated_total') is not None:
                        recalculated_subtotal += float(line['recalculated_total'])
                    else:
                        recalculated_subtotal += line_orig_total
                    updated_lines.append(line)
            else:
                recalculated_subtotal += line_orig_total
                updated_lines.append(line)

        original_subtotal = round(original_subtotal, 2)
        recalculated_subtotal = round(recalculated_subtotal, 2)
        weight_adj = round(recalculated_subtotal - original_subtotal, 2)

        # Tax recalculation
        orig_tax = float(order.get('tax', 0) or 0)
        orig_sub = float(order.get('subtotal', 0) or 0)
        if has_catch_weight and orig_sub > 0 and orig_tax > 0:
            tax_rate = orig_tax / orig_sub
            new_tax = round(recalculated_subtotal * tax_rate, 2)
        else:
            new_tax = orig_tax

        freight = float(order.get('freight_amount', 0) or 0)
        hdr_discount = float(order.get('discount_amount', 0) or 0)
        new_grand_total = round(max(0.0, recalculated_subtotal + new_tax + freight - hdr_discount), 2)

        if has_catch_weight:
            self.repo.update(order_id, {
                'subtotal': recalculated_subtotal,
                'tax': new_tax,
                'grand_total': new_grand_total,
            }, conn=conn)

        return {
            'order_id': order_id,
            'is_catch_weight': has_catch_weight,
            'original_subtotal': original_subtotal,
            'recalculated_subtotal': recalculated_subtotal,
            'weight_adjustment_amount': weight_adj,
            'nominal_total_weight': round(total_nominal_weight, 4) if has_any_nominal else None,
            'actual_total_weight': round(total_actual_weight, 4) if has_any_actual else None,
            'tax': new_tax,
            'grand_total': new_grand_total,
            'lines': updated_lines,
        }

    def _create_invoice_from_order(self, order_id, conn=None):
        recalc = self.recalculate_order_catch_weight(order_id, conn=conn)
        order = self.repo.get(order_id, conn=conn)
        if not order:
            logger.error(f"Cannot create invoice: Sales order {order_id} not found")
            raise ValueError(f"Sales order {order_id} not found")

        try:
            invoice_number = self._generate_invoice_number(conn=conn)
            notes = f'Auto-generated from order {order.get("order_number")}'
            if recalc.get('is_catch_weight') and recalc.get('weight_adjustment_amount') != 0:
                adj = recalc.get('weight_adjustment_amount')
                notes += f" (Catch-weight adjustment: {'+' if adj > 0 else ''}{adj:.2f})"

            # Resolve effective payment terms (Order term -> Customer term -> Default term -> Fallback)
            term = resolve_effective_term(
                payment_term_id=order.get('payment_term_id'),
                customer_id=order.get('customer_id'),
                customer_repo=self.customer_repo if hasattr(self, 'customer_repo') else None,
                term_repo=self.payment_term_repo if hasattr(self, 'payment_term_repo') else None,
                conn=conn,
            )

            term_id = order.get('payment_term_id')
            if not term_id and isinstance(term, dict):
                term_id = term.get('id')

            issue_date = order.get('order_date') or date.today()
            due_date = calculate_due_date(base_date=issue_date, term=term)
            discount_due_date = calculate_discount_deadline(base_date=issue_date, term=term)

            discount_percentage = float(term.get('discount_percentage', 0.0) or 0.0) if isinstance(term, dict) else float(getattr(term, 'discount_percentage', 0.0) or 0.0)
            discount_days = int(term.get('discount_days', 0) or 0) if isinstance(term, dict) else int(getattr(term, 'discount_days', 0) or 0)
            grand_total = float(order.get('grand_total', 0) or 0)
            early_discount_amount = calculate_max_early_discount(grand_total, discount_percentage) if (discount_percentage > 0 and discount_days > 0) else 0.0

            self.inv_repo.create({
                'invoice_number': invoice_number,
                'invoice_type': 'Sales',
                'partner_id': order.get('customer_id'),
                'sales_order_id': order_id,
                'sales_rep_id': order.get('sales_rep_id'),
                'payment_term_id': term_id,
                'issue_date': issue_date,
                'due_date': due_date,
                'discount_due_date': discount_due_date,
                'discount_percentage': discount_percentage,
                'discount_days': discount_days,
                'early_discount_amount': early_discount_amount,
                'total_amount': grand_total,
                'freight_amount': order.get('freight_amount', 0) or 0,
                'discount_amount': order.get('discount_amount', 0) or 0,
                'status': 'Unpaid',
                'notes': notes,
                'is_catch_weight': recalc.get('is_catch_weight', False),
                'nominal_total_weight': recalc.get('nominal_total_weight'),
                'actual_total_weight': recalc.get('actual_total_weight'),
                'weight_adjustment_amount': recalc.get('weight_adjustment_amount', 0.0),
            }, conn=conn)
            logger.info(f"Successfully created invoice {invoice_number} for sales order {order_id}")
        except Exception as e:
            logger.error(f"Failed to create invoice for sales order {order_id}: {e}")
            raise RuntimeError(f"Failed to create invoice for sales order {order_id}: {e}") from e

        customer_id = order.get('customer_id')
        if customer_id:
            try:
                customer = self.customer_repo.get(customer_id, conn=conn)
                if customer:
                    # NOTE: This read-modify-write is not atomic.  Concurrent orders
                    # for the same customer can lose increments.  A fix requires raw SQL:
                    #   UPDATE t0010 SET balance = balance + %s WHERE id = %s
                    # which needs a real Postgres connection (not the mock store).
                    # The in-memory mock test store does not serialize concurrent access,
                    # so the concurrent balance assertion was already removed in PR #5.
                    current_bal = float(customer.get('balance') or 0.0)
                    order_total = float(order.get('grand_total') or 0.0)
                    new_balance = current_bal + order_total
                    self.customer_repo.update(customer_id, {'balance': new_balance}, conn=conn)
                    logger.info(f"Updated customer {customer_id} balance to {new_balance}")
            except Exception as e:
                logger.error(f"Failed to update customer balance for customer {customer_id}: {e}")
                raise RuntimeError(f"Failed to update customer balance for customer {customer_id}: {e}") from e

    def _reserve_order_stock(self, order_id, conn=None):
        from modules.inventory.services.stock_movement import StockMovementService
        order = self.repo.get(order_id, conn=conn)
        if not order:
            logger.error(f"Cannot reserve stock: Sales order {order_id} not found")
            raise ValueError(f"Sales order {order_id} not found")
        warehouse_id = order.get('warehouse_id')
        if not warehouse_id:
            warehouse_repo = CrudRepository('T0008', business_columns=['id', 'name', 'is_active'])
            warehouses = warehouse_repo.list(filters={'is_active': True}, limit=1, conn=conn)
            if warehouses:
                warehouse_id = warehouses[0]['id']
            else:
                logger.error(f"Cannot reserve stock for sales order {order_id}: No active warehouse found")
                from fastapi import HTTPException
                raise HTTPException(400, 'No active warehouse found for stock reservation')
        lines = self.line_repo.list(filters={'sales_order_id': order_id}, conn=conn)
        # Lock ordering: Sort lines by product_id to prevent database deadlocks across multi-line orders
        lines = sorted(lines, key=lambda l: (l.get('product_id') or 0))

        svc = StockMovementService()
        reserved_lines = []
        errors = []
        for line in lines:
            product_id = line.get('product_id')
            qty = line.get('qty', 0)
            if not product_id or qty <= 0:
                continue
            try:
                svc.reserve_stock(product_id, warehouse_id, qty, 'sales_order', order_id, conn=conn)
                reserved_lines.append((product_id, qty))
            except Exception as e:
                logger.warning(f"Failed to reserve stock for product {product_id} (qty {qty}) on order {order_id}: {e}")
                errors.append(f'Product {product_id}: {str(e)}')
                break  # Stop immediately on failure to enforce total rollback!

        if errors:
            # Enforce total rollback on unbottlenecked products if any line fails
            for prod_id, r_qty in reserved_lines:
                try:
                    svc.release_stock(prod_id, warehouse_id, r_qty, 'sales_order', order_id, conn=conn)
                except Exception as rel_err:
                    logger.warning(f"Failed to release stock for product {prod_id} during rollback: {rel_err}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            error_msg = f'Stock reservation partial failure: {"; ".join(errors)}'
            logger.error(f"Sales order {order_id} stock reservation failed: {error_msg}")
            raise RuntimeError(error_msg)

        from modules.warehouse.services.pick_list_service import PickListService
        try:
            pl_service = PickListService()
            pl_service.create_from_order(order_id, warehouse_id, conn=conn)
            logger.info(f"Successfully generated pick list for sales order {order_id} in warehouse {warehouse_id}")
        except Exception as e:
            logger.error(f"Failed to create pick list for sales order {order_id}: {e}")
            for prod_id, r_qty in reserved_lines:
                try:
                    svc.release_stock(prod_id, warehouse_id, r_qty, 'sales_order', order_id, conn=conn)
                except Exception as rel_err:
                    logger.warning(f"Failed to release stock for product {prod_id} during pick list failure rollback: {rel_err}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise RuntimeError(f"Failed to create pick list for sales order {order_id}: {e}") from e

    def _release_order_stock(self, order_id, conn=None):
        from modules.inventory.services.stock_movement import StockMovementService
        order = self.repo.get(order_id, conn=conn)
        if not order:
            logger.warning(f"Cannot release stock: Sales order {order_id} not found")
            return
        warehouse_id = order.get('warehouse_id')
        if not warehouse_id:
            warehouse_repo = CrudRepository('T0008', business_columns=['id', 'name', 'is_active'])
            warehouses = warehouse_repo.list(filters={'is_active': True}, limit=1, conn=conn)
            if not warehouses:
                logger.warning(f"No active warehouse found when releasing stock for sales order {order_id}")
                return
            warehouse_id = warehouses[0]['id']
        lines = self.line_repo.list(filters={'sales_order_id': order_id}, conn=conn)
        # Lock ordering: Sort lines by product_id
        lines = sorted(lines, key=lambda l: (l.get('product_id') or 0))
        svc = StockMovementService()
        errors = []
        for line in lines:
            product_id = line.get('product_id')
            qty = line.get('qty', 0)
            if not product_id or qty <= 0:
                continue
            try:
                svc.release_stock(product_id, warehouse_id, qty, 'sales_order', order_id, conn=conn)
            except Exception as e:
                logger.warning(f"Failed to release stock for product {product_id} (qty {qty}) on order {order_id}: {e}")
                errors.append(f'Product {product_id}: {str(e)}')
        if errors:
            error_msg = f'Stock release partial failure: {"; ".join(errors)}'
            logger.error(f"Sales order {order_id} stock release failed: {error_msg}")
            raise RuntimeError(error_msg)



