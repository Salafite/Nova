import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Union
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.database.sequence import generate_invoice_number
from modules.accounting.services.payment_term_service import (
    calculate_due_date,
    calculate_discount_deadline,
    calculate_max_early_discount,
    resolve_effective_term,
    PAYMENT_TERM_REPO,
)

logger = logging.getLogger(__name__)

INVOICE_REPO = CrudRepository(
    'T0090',
    business_columns=[
        'id',
        'invoice_number',
        'invoice_type',
        'partner_id',
        'sales_order_id',
        'sales_rep_id',
        'payment_term_id',
        'issue_date',
        'due_date',
        'discount_due_date',
        'discount_percentage',
        'discount_days',
        'early_discount_amount',
        'total_amount',
        'freight_amount',
        'discount_amount',
        'status',
        'notes',
        'is_catch_weight',
        'nominal_total_weight',
        'actual_total_weight',
        'weight_adjustment_amount',
    ],
)


CUSTOMER_REPO = CrudRepository(
    'T0010',
    business_columns=['id', 'name', 'credit_limit', 'balance', 'payment_term_id'],
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
        'payment_term_id',
        'status',
        'order_date',
        'notes',
    ],
)

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


class InvoiceService(CrudService):
    def __init__(
        self,
        repo: CrudRepository = None,
        customer_repo: CrudRepository = None,
        order_repo: CrudRepository = None,
        line_repo: CrudRepository = None,
        pl_repo: CrudRepository = None,
        pli_repo: CrudRepository = None,
        payment_term_repo: CrudRepository = None,
    ):
        super().__init__(repo or INVOICE_REPO)
        self.customer_repo = customer_repo or CUSTOMER_REPO
        self.order_repo = order_repo or ORDER_REPO
        self.line_repo = line_repo or LINE_REPO
        self.pl_repo = pl_repo or PL_REPO
        self.pli_repo = pli_repo or PLI_REPO
        self.payment_term_repo = payment_term_repo or PAYMENT_TERM_REPO

    def validate_order_tolerance_approvals(self, order_id: int, conn=None):
        """
        Validate that all pick list items for the sales order have no unapproved catch-weight tolerance discrepancies.
        Raises ValueError if unapproved discrepancies are found.
        """
        if not order_id or not hasattr(self, 'pl_repo') or not self.pl_repo:
            return
        kwargs = {'conn': conn} if conn is not None else {}
        try:
            pick_lists = self.pl_repo.list(filters={'sales_order_id': order_id}, **kwargs)
        except Exception as e:
            logger.warning(f"Could not check pick lists for order {order_id}: {e}")
            return

        for pl in pick_lists:
            if hasattr(self, 'pli_repo') and self.pli_repo:
                try:
                    items = self.pli_repo.list(filters={'pick_list_id': pl['id']}, **kwargs)
                    unapproved = [
                        it for it in items
                        if it.get('tolerance_status') == 'Out of Tolerance' and not it.get('supervisor_approved')
                    ]
                    if unapproved:
                        names = [it.get('product_name') or f"Item #{it.get('id')}" for it in unapproved]
                        msg = f"Cannot invoice order {order_id}: Unapproved catch-weight tolerance discrepancies exist on pick list #{pl.get('id')} items: {', '.join(names)}"
                        logger.warning(msg)
                        raise ValueError(msg)
                except ValueError:
                    raise
                except Exception as e:
                    logger.warning(f"Could not check pick list items for pick list {pl['id']}: {e}")

    def create(self, payload: dict, conn=None):
        if not payload.get('invoice_number') or not str(payload.get('invoice_number')).strip():
            payload['invoice_number'] = generate_invoice_number(conn=conn)
        sales_order_id = payload.get('sales_order_id')
        if sales_order_id:
            self.validate_order_tolerance_approvals(sales_order_id, conn=conn)

        # Ensure issue_date is populated
        issue_date = payload.get('issue_date') or date.today()
        if not payload.get('issue_date'):
            payload['issue_date'] = issue_date

        # Resolve effective payment term
        order_term_id = None
        if not payload.get('payment_term_id') and sales_order_id and hasattr(self, 'order_repo') and self.order_repo:
            try:
                order_rec = self.order_repo.get(sales_order_id, conn=conn)
                if order_rec and order_rec.get('payment_term_id'):
                    order_term_id = order_rec.get('payment_term_id')
            except Exception as e:
                logger.warning(f"Could not fetch order {sales_order_id} for payment term resolution: {e}")

        effective_term_id = payload.get('payment_term_id') or order_term_id
        term = resolve_effective_term(
            payment_term_id=effective_term_id,
            customer_id=payload.get('partner_id'),
            customer_repo=self.customer_repo if hasattr(self, 'customer_repo') else None,
            term_repo=self.payment_term_repo if hasattr(self, 'payment_term_repo') else None,
            conn=conn,
        )

        if not payload.get('payment_term_id'):
            if isinstance(term, dict) and term.get('id'):
                payload['payment_term_id'] = term.get('id')
            elif hasattr(term, 'id') and getattr(term, 'id', None):
                payload['payment_term_id'] = getattr(term, 'id')

        # Dynamically compute due_date if omitted
        if not payload.get('due_date'):
            payload['due_date'] = calculate_due_date(base_date=issue_date, term=term)

        # Dynamically compute discount cutoff if omitted
        if payload.get('discount_due_date') is None:
            payload['discount_due_date'] = calculate_discount_deadline(base_date=issue_date, term=term)

        # Dynamically populate discount percentage & discount days if omitted
        if payload.get('discount_percentage') is None:
            term_pct = (
                float(term.get('discount_percentage', 0.0) or 0.0)
                if isinstance(term, dict)
                else float(getattr(term, 'discount_percentage', 0.0) or 0.0)
            )
            payload['discount_percentage'] = term_pct

        if payload.get('discount_days') is None:
            term_days = (
                int(term.get('discount_days', 0) or 0)
                if isinstance(term, dict)
                else int(getattr(term, 'discount_days', 0) or 0)
            )
            payload['discount_days'] = term_days

        # Compute early discount amount if eligible
        if payload.get('early_discount_amount') is None:
            pct = float(payload.get('discount_percentage', 0.0) or 0.0)
            days = int(payload.get('discount_days', 0) or 0)
            total = float(payload.get('total_amount', 0.0) or 0.0)
            if pct > 0 and days > 0 and total > 0:
                payload['early_discount_amount'] = calculate_max_early_discount(total, pct)
            else:
                payload['early_discount_amount'] = 0.0

        return super().create(payload, conn=conn)

    def calculate_catch_weight_summary(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate total nominal weight, total actual weight, and weight adjustment amount from lines.
        Returns:
            {
                'is_catch_weight': bool,
                'nominal_total_weight': Optional[float],
                'actual_total_weight': Optional[float],
                'weight_adjustment_amount': float,
                'recalculated_subtotal': float,
                'original_subtotal': float,
                'lines': List[Dict[str, Any]],
            }
        """
        has_cw = False
        has_nominal = False
        has_actual = False
        tot_nominal = 0.0
        tot_actual = 0.0
        orig_sub = 0.0
        recalc_sub = 0.0
        processed_lines = []

        for line in lines:
            line_tot = float(line.get('line_total', 0) or 0)
            orig_sub += line_tot

            if line.get('is_catch_weight'):
                has_cw = True
                nom_w = line.get('nominal_weight')
                act_w = line.get('catch_weight_actual')

                if nom_w is not None:
                    tot_nominal += float(nom_w)
                    has_nominal = True

                if act_w is not None:
                    tot_actual += float(act_w)
                    has_actual = True
                    recalc_tot = line.get('recalculated_total')
                    if recalc_tot is not None:
                        line_recalc = float(recalc_tot)
                    else:
                        rate = float(line.get('unit_price_pricing_uom') or line.get('unit_price') or 0)
                        discount = float(line.get('discount', 0) or 0)
                        line_recalc = round(max(0.0, (float(act_w) * rate) - discount), 2)
                    recalc_sub += line_recalc
                    processed_line = dict(line, recalculated_total=line_recalc)
                else:
                    recalc_sub += line_tot
                    processed_line = line
            else:
                recalc_sub += line_tot
                processed_line = line
            processed_lines.append(processed_line)

        orig_sub = round(orig_sub, 2)
        recalc_sub = round(recalc_sub, 2)
        adj = round(recalc_sub - orig_sub, 2)

        return {
            'is_catch_weight': has_cw,
            'nominal_total_weight': round(tot_nominal, 4) if has_nominal else None,
            'actual_total_weight': round(tot_actual, 4) if has_actual else None,
            'weight_adjustment_amount': adj,
            'original_subtotal': orig_sub,
            'recalculated_subtotal': recalc_sub,
            'lines': processed_lines,
        }

    def create_from_order(
        self,
        order: dict,
        recalculation_summary: Optional[dict] = None,
        update_customer_balance: bool = True,
        conn=None,
    ) -> dict:
        """
        Create a sales invoice from an order record, incorporating catch-weight aggregates,
        dynamic payment terms due date & discount calculations, and customer balance updates.
        """
        recalc = recalculation_summary or {}
        is_cw = recalc.get('is_catch_weight', order.get('is_catch_weight', False))
        weight_adj = recalc.get('weight_adjustment_amount', 0.0)

        notes = f'Auto-generated from order {order.get("order_number")}'
        if is_cw and weight_adj != 0:
            notes += f" (Catch-weight adjustment: {'+' if weight_adj > 0 else ''}{weight_adj:.2f})"

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
        elif not term_id and hasattr(term, 'id'):
            term_id = getattr(term, 'id', None)

        issue_date = order.get('order_date') or date.today()
        due_date = calculate_due_date(base_date=issue_date, term=term)
        discount_due_date = calculate_discount_deadline(base_date=issue_date, term=term)

        discount_percentage = (
            float(term.get('discount_percentage', 0.0) or 0.0)
            if isinstance(term, dict)
            else float(getattr(term, 'discount_percentage', 0.0) or 0.0)
        )
        discount_days = (
            int(term.get('discount_days', 0) or 0)
            if isinstance(term, dict)
            else int(getattr(term, 'discount_days', 0) or 0)
        )
        grand_total = float(order.get('grand_total', 0) or 0)
        early_discount_amount = (
            calculate_max_early_discount(grand_total, discount_percentage)
            if (discount_percentage > 0 and discount_days > 0)
            else 0.0
        )

        invoice_payload = {
            'invoice_type': 'Sales',
            'partner_id': order.get('customer_id'),
            'sales_order_id': order.get('id'),
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
            'is_catch_weight': is_cw,
            'nominal_total_weight': recalc.get('nominal_total_weight'),
            'actual_total_weight': recalc.get('actual_total_weight'),
            'weight_adjustment_amount': weight_adj,
        }
        invoice = self.create(invoice_payload, conn=conn)

        if update_customer_balance and order.get('customer_id') and self.customer_repo:
            try:
                cust_id = order['customer_id']
                customer = self.customer_repo.get(cust_id, conn=conn)
                if customer:
                    new_balance = float(customer.get('balance', 0) or 0) + float(order.get('grand_total', 0) or 0)
                    self.customer_repo.update(cust_id, {'balance': new_balance}, conn=conn)
                    logger.info(f"Updated customer {cust_id} balance to {new_balance}")
            except Exception as e:
                logger.error(f"Failed to update customer balance for customer {order.get('customer_id')}: {e}")
                raise RuntimeError(f"Failed to update customer balance: {e}") from e

        return invoice

    def recalculate_and_invoice_order(
        self,
        order_id: int,
        update_customer_balance: bool = True,
        conn=None,
    ) -> dict:
        """
        Recalculate order billing based on catch-weight lines and create invoice.
        """
        order = self.order_repo.get(order_id, conn=conn)
        if not order:
            logger.error(f"Cannot recalculate and invoice order: order {order_id} not found")
            raise ValueError(f"Sales order {order_id} not found")

        lines = self.line_repo.list(filters={'sales_order_id': order_id}, conn=conn)
        summary = self.calculate_catch_weight_summary(lines)

        if summary.get('is_catch_weight'):
            orig_sub = float(order.get('subtotal', 0) or 0)
            orig_tax = float(order.get('tax', 0) or 0)
            recalc_sub = summary.get('recalculated_subtotal', orig_sub)

            if orig_sub > 0 and orig_tax > 0:
                tax_rate = orig_tax / orig_sub
                new_tax = round(recalc_sub * tax_rate, 2)
            else:
                new_tax = orig_tax

            freight = float(order.get('freight_amount', 0) or 0)
            discount = float(order.get('discount_amount', 0) or 0)
            new_grand_total = round(max(0.0, recalc_sub + new_tax + freight - discount), 2)

            order['subtotal'] = recalc_sub
            order['tax'] = new_tax
            order['grand_total'] = new_grand_total
            order['is_catch_weight'] = True

            self.order_repo.update(order_id, {
                'subtotal': recalc_sub,
                'tax': new_tax,
                'grand_total': new_grand_total,
            }, conn=conn)

            # Update line items with recalculated totals
            for l in summary.get('lines', []):
                if l.get('is_catch_weight') and l.get('recalculated_total') is not None:
                    self.line_repo.update(l['id'], {
                        'is_catch_weight': True,
                        'recalculated_total': l['recalculated_total'],
                        'catch_weight_actual': l.get('catch_weight_actual'),
                    }, conn=conn)

        return self.create_from_order(
            order,
            recalculation_summary=summary,
            update_customer_balance=update_customer_balance,
            conn=conn,
        )

    def get_catch_weight_breakdown(self, invoice_id: int, conn=None) -> dict:
        """
        Retrieve catch-weight breakdown details for an invoice.
        """
        inv = self.repo.get(invoice_id, conn=conn)
        if not inv:
            raise ValueError(f"Invoice {invoice_id} not found")

        sales_order_id = inv.get('sales_order_id')
        lines = []
        if sales_order_id:
            lines = self.line_repo.list(filters={'sales_order_id': sales_order_id}, conn=conn)

        return {
            'invoice_id': invoice_id,
            'invoice_number': inv.get('invoice_number'),
            'is_catch_weight': bool(inv.get('is_catch_weight')),
            'nominal_total_weight': inv.get('nominal_total_weight'),
            'actual_total_weight': inv.get('actual_total_weight'),
            'weight_adjustment_amount': float(inv.get('weight_adjustment_amount', 0) or 0),
            'total_amount': float(inv.get('total_amount', 0) or 0),
            'sales_order_id': sales_order_id,
            'lines': lines,
        }

