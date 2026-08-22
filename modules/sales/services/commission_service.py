import os
import uuid
import logging
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import date
from ..models.commission import (
    CommissionRuleCreate,
    CommissionRuleUpdate,
    CommissionRuleResponse,
    CommissionPayoutCreate,
    CommissionPayoutUpdate,
    CommissionPayoutResponse,
    CommissionCalculationRequest,
    CommissionStatementItem,
    CommissionStatementResponse,
    CommissionSummaryItem,
)
from ..repositories.commission_repo import (
    CommissionRepository,
    commission_repo as default_repo,
)
from modules.core.services.base import CrudService

logger = logging.getLogger(__name__)


def determine_commission_rate(margin_pct: float, rule: Dict[str, Any]) -> float:
    """
    Evaluates tiered commission rules or minimum margin threshold to compute the
    applicable commission percentage rate.
    """
    tier_rules = rule.get('tier_rules') or []
    if isinstance(tier_rules, list) and tier_rules:
        for tier in tier_rules:
            min_margin = float(tier.get('min_margin_pct', 0.0) or 0.0)
            max_margin = tier.get('max_margin_pct')
            rate = float(tier.get('commission_rate', 0.0) or 0.0)
            if margin_pct >= min_margin:
                if max_margin is None or margin_pct <= float(max_margin):
                    return rate

    # Threshold fallback
    min_threshold = float(rule.get('min_margin_threshold', 15.00) or 0.0)
    if margin_pct >= min_threshold:
        return float(rule.get('base_commission_rate', 5.00) or 0.0)

    return 0.0


def calculate_discount_penalty(
    gross_commission: float,
    discount_pct: float,
    discount_penalty_rate: float,
) -> float:
    """
    Calculates the commission penalty for customer discounts granted.
    Formula: gross_commission * (discount_pct * discount_penalty_rate / 100.0)
    """
    if gross_commission <= 0 or discount_pct <= 0 or discount_penalty_rate <= 0:
        return 0.0
    penalty = gross_commission * ((discount_pct * discount_penalty_rate) / 100.0)
    return round(min(gross_commission, penalty), 2)


class CommissionService:
    """
    Core business engine for collected gross margin sales representative commission calculations,
    tier rule evaluations, discount penalties, statements, and payouts.
    """

    def __init__(self, repo: Optional[CommissionRepository] = None):
        self.repo = repo or default_repo

    # -----------------------------------------------------------------------
    # Commission Calculation & Statements
    # -----------------------------------------------------------------------

    def calculate_statement(
        self,
        sales_rep_id: int,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        rule_id: Optional[int] = None,
        include_pending: bool = True,
        conn=None,
    ) -> CommissionStatementResponse:
        """
        Calculates comprehensive commission statement for a sales representative based strictly
        on realized gross profit from paid invoices and collected cash.
        """
        rep_info = self.repo.get_sales_rep_info(sales_rep_id, conn=conn) or {}
        rep_name = rep_info.get('full_name', f'Sales Rep #{sales_rep_id}')
        rep_email = rep_info.get('email')

        # Resolve active rule
        if rule_id:
            rule = self.repo.get_rule(rule_id, conn=conn) or self.repo.get_active_rule_for_rep(sales_rep_id, conn=conn)
        else:
            rule = self.repo.get_active_rule_for_rep(sales_rep_id, conn=conn)

        rule_name = rule.get('rule_name', 'Standard Commission Plan')
        penalty_rate = float(rule.get('discount_penalty_rate', 0.50) or 0.50)

        rows = self.repo.get_sales_rep_invoices_and_payments(
            sales_rep_id=sales_rep_id,
            period_start=period_start,
            period_end=period_end,
            include_pending=include_pending,
            conn=conn,
        )

        items: List[CommissionStatementItem] = []

        for r in rows:
            gross_sales = round(float(r.get('gross_sales', 0.0)), 2)
            discount_amount = round(float(r.get('discount_amount', 0.0)), 2)
            cogs = round(float(r.get('cogs', 0.0)), 2)
            freight_cost = round(float(r.get('freight_cost', 0.0)), 2)
            invoice_total = round(float(r.get('invoice_total', 0.0)), 2)
            collected_cash = round(float(r.get('collected_cash', 0.0)), 2)

            net_revenue = round(max(0.0, gross_sales - discount_amount), 2)
            gross_profit = round(net_revenue - cogs - freight_cost, 2)
            realized_margin_pct = round((gross_profit / net_revenue * 100.0), 2) if net_revenue > 0 else 0.0

            # Realized gross profit proportional to collected cash
            if invoice_total > 0 and collected_cash > 0:
                collection_ratio = min(1.0, collected_cash / invoice_total)
                realized_gross_margin = round(gross_profit * collection_ratio, 2)
            else:
                realized_gross_margin = 0.0

            # Commission rate & discount penalty
            commission_rate = determine_commission_rate(realized_margin_pct, rule)
            gross_commission = (
                round(realized_gross_margin * (commission_rate / 100.0), 2)
                if realized_gross_margin > 0
                else 0.0
            )

            discount_pct = round((discount_amount / gross_sales * 100.0), 2) if gross_sales > 0 else 0.0
            discount_penalty = calculate_discount_penalty(gross_commission, discount_pct, penalty_rate)
            net_commission = round(max(0.0, gross_commission - discount_penalty), 2)

            # Determine item payout / collection status
            payout_status = r.get('payout_status')
            if payout_status == 'Paid':
                status = 'Paid'
            elif payout_status == 'Approved':
                status = 'Approved'
            elif collected_cash >= invoice_total and invoice_total > 0:
                status = 'Collected'
            elif collected_cash > 0:
                status = 'Partial'
            else:
                status = 'Pending'

            items.append(
                CommissionStatementItem(
                    invoice_id=r.get('invoice_id'),
                    invoice_number=r.get('invoice_number'),
                    order_number=r.get('order_number'),
                    payment_id=r.get('latest_payment_id'),
                    payment_date=r.get('latest_payment_date'),
                    customer_id=r.get('customer_id'),
                    customer_name=r.get('customer_name'),
                    invoice_total=invoice_total,
                    collected_cash=collected_cash,
                    cogs=cogs,
                    freight_cost=freight_cost,
                    discount_amount=discount_amount,
                    realized_gross_margin=realized_gross_margin,
                    realized_margin_pct=realized_margin_pct,
                    commission_rate=commission_rate,
                    gross_commission=gross_commission,
                    discount_penalty=discount_penalty,
                    net_commission=net_commission,
                    status=status,
                )
            )

        # Compute statement summary totals
        total_booked_sales = round(sum(it.invoice_total for it in items), 2)
        total_collected = round(sum(it.collected_cash for it in items), 2)
        total_cogs = round(sum(it.cogs for it in items), 2)
        total_freight = round(sum(it.freight_cost for it in items), 2)
        total_discounts = round(sum(it.discount_amount for it in items), 2)
        total_realized_margin = round(sum(it.realized_gross_margin for it in items), 2)
        avg_margin_pct = (
            round((total_realized_margin / total_collected * 100.0), 2)
            if total_collected > 0
            else 0.0
        )
        gross_commission_total = round(sum(it.gross_commission for it in items), 2)
        total_penalties = round(sum(it.discount_penalty for it in items), 2)
        net_payable = round(sum(it.net_commission for it in items), 2)
        paid_amount = round(sum(it.net_commission for it in items if it.status == 'Paid'), 2)
        pending_amount = round(max(0.0, net_payable - paid_amount), 2)

        return CommissionStatementResponse(
            sales_rep_id=sales_rep_id,
            sales_rep_name=rep_name,
            sales_rep_email=rep_email,
            period_start=period_start,
            period_end=period_end,
            rule_name=rule_name,
            total_booked_sales=total_booked_sales,
            total_collected_amount=total_collected,
            total_cogs=total_cogs,
            total_freight_cost=total_freight,
            total_discounts_granted=total_discounts,
            total_realized_gross_margin=total_realized_margin,
            average_realized_margin_pct=avg_margin_pct,
            gross_commission_earned=gross_commission_total,
            total_discount_penalties=total_penalties,
            net_commission_payable=net_payable,
            paid_commission_amount=paid_amount,
            pending_commission_amount=pending_amount,
            items=items,
        )

    def get_commission_summaries(
        self,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        sales_rep_id: Optional[int] = None,
        conn=None,
    ) -> List[CommissionSummaryItem]:
        """
        Aggregates summary commission balances and collected margin statistics across all sales reps
        or for a specific sales representative.
        """
        if sales_rep_id is not None:
            reps = [self.repo.get_sales_rep_info(sales_rep_id, conn=conn) or {'id': sales_rep_id, 'full_name': f'Sales Rep #{sales_rep_id}', 'email': None}]
        else:
            reps = self.repo.list_all_sales_reps(conn=conn)

        summaries: List[CommissionSummaryItem] = []

        for rep in reps:
            rep_id = rep['id']
            stmt = self.calculate_statement(
                sales_rep_id=rep_id,
                period_start=period_start,
                period_end=period_end,
                include_pending=True,
                conn=conn,
            )

            summaries.append(
                CommissionSummaryItem(
                    sales_rep_id=rep_id,
                    sales_rep_name=stmt.sales_rep_name or rep.get('full_name', f'Sales Rep #{rep_id}'),
                    sales_rep_email=stmt.sales_rep_email or rep.get('email'),
                    total_invoices=len(stmt.items),
                    total_collected=stmt.total_collected_amount,
                    total_gross_margin=stmt.total_realized_gross_margin,
                    avg_margin_pct=stmt.average_realized_margin_pct,
                    gross_commission=stmt.gross_commission_earned,
                    discount_penalty=stmt.total_discount_penalties,
                    net_commission=stmt.net_commission_payable,
                    paid_commission=stmt.paid_commission_amount,
                    pending_commission=stmt.pending_commission_amount,
                )
            )

        summaries.sort(key=lambda s: s.net_commission, reverse=True)
        return summaries

    def generate_payouts(
        self,
        sales_rep_id: int,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        rule_id: Optional[int] = None,
        user_id: Optional[int] = None,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """
        Generates formal commission payout ledger records in Nova.t0108 for all unpaid collected
        items for a sales representative in the specified period.
        """
        stmt = self.calculate_statement(
            sales_rep_id=sales_rep_id,
            period_start=period_start,
            period_end=period_end,
            rule_id=rule_id,
            include_pending=False,
            conn=conn,
        )

        payouts_created: List[Dict[str, Any]] = []

        for item in stmt.items:
            if item.net_commission <= 0 or item.status in ('Paid', 'Approved'):
                continue

            payout_number = f"PAY-{sales_rep_id}-{item.invoice_id or 0}-{uuid.uuid4().hex[:6].upper()}"
            payload = {
                'payout_number': payout_number,
                'sales_rep_id': sales_rep_id,
                'invoice_id': item.invoice_id,
                'payment_id': item.payment_id,
                'rule_id': rule_id,
                'period_start': period_start,
                'period_end': period_end,
                'collected_amount': item.collected_cash,
                'realized_gross_margin': item.realized_gross_margin,
                'commission_rate': item.commission_rate,
                'commission_amount': item.gross_commission,
                'discount_penalty': item.discount_penalty,
                'net_commission_amount': item.net_commission,
                'status': 'Pending',
                'payment_date': None,
                'notes': f'Commission payout for Invoice {item.invoice_number or item.invoice_id}',
                'created_by': user_id,
            }
            try:
                res = self.repo.create_payout(payload, conn=conn)
                if res:
                    payouts_created.append(res)
            except Exception as e:
                logger.warning(f"Could not create payout record for invoice {item.invoice_id}: {e}")

        return payouts_created

    # -----------------------------------------------------------------------
    # Rules Management
    # -----------------------------------------------------------------------

    def get_rule(self, rule_id: int, conn=None) -> Optional[Dict[str, Any]]:
        return self.repo.get_rule(rule_id, conn=conn)

    def list_rules(
        self,
        sales_rep_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
        conn=None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        return self.repo.list_rules(
            sales_rep_id=sales_rep_id,
            is_active=is_active,
            limit=limit,
            offset=offset,
            conn=conn,
        )

    def create_rule(self, data: Union[CommissionRuleCreate, dict], user_id: Optional[int] = None, conn=None) -> Dict[str, Any]:
        payload = data.model_dump() if isinstance(data, CommissionRuleCreate) else dict(data)
        if user_id:
            payload['created_by'] = user_id
        return self.repo.create_rule(payload, conn=conn)

    def update_rule(
        self,
        rule_id: int,
        data: Union[CommissionRuleUpdate, dict],
        user_id: Optional[int] = None,
        conn=None,
    ) -> Optional[Dict[str, Any]]:
        payload = data.model_dump(exclude_unset=True) if isinstance(data, CommissionRuleUpdate) else dict(data)
        if user_id:
            payload['updated_by'] = user_id
        return self.repo.update_rule(rule_id, payload, conn=conn)

    def delete_rule(self, rule_id: int, conn=None) -> bool:
        return self.repo.delete_rule(rule_id, conn=conn)

    # -----------------------------------------------------------------------
    # Payouts Management
    # -----------------------------------------------------------------------

    def get_payout(self, payout_id: int, conn=None) -> Optional[Dict[str, Any]]:
        return self.repo.get_payout(payout_id, conn=conn)

    def list_payouts(
        self,
        sales_rep_id: Optional[int] = None,
        status: Optional[str] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        limit: int = 100,
        offset: int = 0,
        conn=None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        return self.repo.list_payouts(
            sales_rep_id=sales_rep_id,
            status=status,
            period_start=period_start,
            period_end=period_end,
            limit=limit,
            offset=offset,
            conn=conn,
        )

    def create_payout(self, data: Union[CommissionPayoutCreate, dict], user_id: Optional[int] = None, conn=None) -> Dict[str, Any]:
        payload = data.model_dump() if isinstance(data, CommissionPayoutCreate) else dict(data)
        if not payload.get('payout_number'):
            payload['payout_number'] = f"PAY-{uuid.uuid4().hex[:8].upper()}"
        if user_id:
            payload['created_by'] = user_id
        return self.repo.create_payout(payload, conn=conn)

    def update_payout(
        self,
        payout_id: int,
        data: Union[CommissionPayoutUpdate, dict],
        user_id: Optional[int] = None,
        conn=None,
    ) -> Optional[Dict[str, Any]]:
        payload = data.model_dump(exclude_unset=True) if isinstance(data, CommissionPayoutUpdate) else dict(data)
        if user_id:
            payload['updated_by'] = user_id
        return self.repo.update_payout(payout_id, payload, conn=conn)

    def approve_payout(self, payout_id: int, user_id: Optional[int] = None, conn=None) -> Optional[Dict[str, Any]]:
        """Approves a pending commission payout."""
        return self.update_payout(payout_id, {'status': 'Approved'}, user_id=user_id, conn=conn)

    def mark_payout_paid(
        self,
        payout_id: int,
        payment_date: Optional[date] = None,
        user_id: Optional[int] = None,
        conn=None,
    ) -> Optional[Dict[str, Any]]:
        """Marks a commission payout as paid."""
        pay_date = payment_date or date.today()
        return self.update_payout(
            payout_id,
            {'status': 'Paid', 'payment_date': pay_date},
            user_id=user_id,
            conn=conn,
        )

    def delete_payout(self, payout_id: int, conn=None) -> bool:
        return self.repo.delete_payout(payout_id, conn=conn)


class CommissionRuleService(CrudService):
    """CRUD Service wrapper for commission rules (T0107)."""
    def __init__(self, repo: Optional[CommissionRepository] = None):
        self.commission_repo = repo or default_repo
        super().__init__(self.commission_repo.rule_repo)


class CommissionPayoutService(CrudService):
    """CRUD Service wrapper for commission payouts (T0108)."""
    def __init__(self, repo: Optional[CommissionRepository] = None):
        self.commission_repo = repo or default_repo
        super().__init__(self.commission_repo.payout_repo)


# Default singleton instances
commission_service = CommissionService()
commission_rule_service = CommissionRuleService()
commission_payout_service = CommissionPayoutService()
