import logging
from typing import Optional, List, Dict, Any
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException, status, Request, Response
from packages.auth.deps import require_permission, get_current_user
from modules.core.controllers.base import apply_pagination_headers
from ..models.commission import (
    CommissionRuleCreate,
    CommissionRuleUpdate,
    CommissionRuleResponse,
    CommissionPayoutCreate,
    CommissionPayoutUpdate,
    CommissionPayoutResponse,
    CommissionCalculationRequest,
    CommissionStatementResponse,
    CommissionSummaryItem,
)
from ..services.commission_service import (
    CommissionService,
    commission_service as default_commission_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix='/api/sales/commission',
    tags=['Sales Commissions'],
    dependencies=[Depends(require_permission('SALES_VIEW'))],
)


# ---------------------------------------------------------------------------
# Commission Statements & Summaries
# ---------------------------------------------------------------------------

@router.get('/statement', response_model=CommissionStatementResponse)
def get_commission_statement(
    sales_rep_id: int = Query(..., description='Sales representative user ID'),
    period_start: Optional[date] = Query(None, description='Period start date (YYYY-MM-DD)'),
    period_end: Optional[date] = Query(None, description='Period end date (YYYY-MM-DD)'),
    rule_id: Optional[int] = Query(None, description='Optional specific commission rule ID'),
    include_pending: bool = Query(True, description='Include pending/uncollected invoices'),
):
    """
    Calculates detailed commission statement for a sales representative based strictly
    on collected cash and realized gross profit from paid invoices.
    """
    return default_commission_service.calculate_statement(
        sales_rep_id=sales_rep_id,
        period_start=period_start,
        period_end=period_end,
        rule_id=rule_id,
        include_pending=include_pending,
    )


@router.get('/summaries', response_model=List[CommissionSummaryItem])
def get_commission_summaries(
    period_start: Optional[date] = Query(None, description='Period start date (YYYY-MM-DD)'),
    period_end: Optional[date] = Query(None, description='Period end date (YYYY-MM-DD)'),
    sales_rep_id: Optional[int] = Query(None, description='Filter by specific sales representative'),
):
    """
    Returns summary commission balances, earned vs paid commission, and realized margin
    statistics for all active sales representatives.
    """
    return default_commission_service.get_commission_summaries(
        period_start=period_start,
        period_end=period_end,
        sales_rep_id=sales_rep_id,
    )


@router.post('/calculate', response_model=CommissionStatementResponse)
def calculate_commission(body: CommissionCalculationRequest):
    """
    Calculates commission statement via structured POST payload.
    """
    if not body.sales_rep_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='sales_rep_id is required for commission statement calculation',
        )
    return default_commission_service.calculate_statement(
        sales_rep_id=body.sales_rep_id,
        period_start=body.period_start,
        period_end=body.period_end,
        rule_id=body.rule_id,
        include_pending=body.include_pending,
    )


@router.post('/payouts/generate')
def generate_commission_payouts(
    sales_rep_id: int = Query(..., description='Sales representative user ID'),
    period_start: Optional[date] = Query(None, description='Period start date'),
    period_end: Optional[date] = Query(None, description='Period end date'),
    rule_id: Optional[int] = Query(None, description='Commission rule override ID'),
    user: dict = Depends(get_current_user),
):
    """
    Generates formal pending commission payout records for all unpaid collected items.
    """
    created_payouts = default_commission_service.generate_payouts(
        sales_rep_id=sales_rep_id,
        period_start=period_start,
        period_end=period_end,
        rule_id=rule_id,
        user_id=user.get('id'),
    )
    return {
        'message': f'Successfully generated {len(created_payouts)} commission payout records',
        'count': len(created_payouts),
        'payouts': created_payouts,
    }


# ---------------------------------------------------------------------------
# Commission Rules Management (Nova.t0109)
# ---------------------------------------------------------------------------

@router.get('/rules')
def list_commission_rules(
    response: Response,
    request: Request,
    sales_rep_id: Optional[int] = Query(None, description='Filter rules for sales rep'),
    is_active: Optional[bool] = Query(None, description='Filter active/inactive rules'),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return (1-500, default 50)"),
    offset: int = Query(0, ge=0, description="Number of records to skip (default 0)"),
):
    """
    Lists commission configuration plans and rate rules.
    """
    limit = min(max(1, limit), 500) if limit is not None else 50
    offset = max(0, offset) if offset is not None else 0
    items, total = default_commission_service.list_rules(
        sales_rep_id=sales_rep_id,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    apply_pagination_headers(
        response=response,
        request=request,
        total_count=total,
        limit=limit,
        offset=offset,
    )
    return {'items': items, 'total': total, 'limit': limit, 'offset': offset}


@router.post('/rules', status_code=status.HTTP_201_CREATED)
def create_commission_rule(
    body: CommissionRuleCreate,
    user: dict = Depends(get_current_user),
):
    """
    Creates a new commission configuration rule plan.
    """
    return default_commission_service.create_rule(body, user_id=user.get('id'))


@router.get('/rules/{rule_id}')
def get_commission_rule(rule_id: int):
    """
    Retrieves a single commission rule by ID.
    """
    rule = default_commission_service.get_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Commission rule #{rule_id} not found',
        )
    return rule


@router.put('/rules/{rule_id}')
def update_commission_rule(
    rule_id: int,
    body: CommissionRuleUpdate,
    user: dict = Depends(get_current_user),
):
    """
    Updates an existing commission configuration rule plan.
    """
    rule = default_commission_service.update_rule(rule_id, body, user_id=user.get('id'))
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Commission rule #{rule_id} not found',
        )
    return rule


@router.delete('/rules/{rule_id}')
def delete_commission_rule(rule_id: int):
    """
    Soft-deletes / deactivates a commission rule plan.
    """
    success = default_commission_service.delete_rule(rule_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Commission rule #{rule_id} not found',
        )
    return {'message': f'Commission rule #{rule_id} deleted successfully', 'success': True}


# ---------------------------------------------------------------------------
# Commission Payouts & Ledger (Nova.t0110)
# ---------------------------------------------------------------------------

@router.get('/payouts')
def list_commission_payouts(
    response: Response,
    request: Request,
    sales_rep_id: Optional[int] = Query(None, description='Filter payouts by sales rep ID'),
    payout_status: Optional[str] = Query(None, alias='status', description='Filter by status: Pending, Approved, Paid, Cancelled'),
    period_start: Optional[date] = Query(None, description='Filter payouts from period start date'),
    period_end: Optional[date] = Query(None, description='Filter payouts to period end date'),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return (1-500, default 50)"),
    offset: int = Query(0, ge=0, description="Number of records to skip (default 0)"),
):
    """
    Lists commission payout ledger records.
    """
    limit = min(max(1, limit), 500) if limit is not None else 50
    offset = max(0, offset) if offset is not None else 0
    items, total = default_commission_service.list_payouts(
        sales_rep_id=sales_rep_id,
        status=payout_status,
        period_start=period_start,
        period_end=period_end,
        limit=limit,
        offset=offset,
    )
    apply_pagination_headers(
        response=response,
        request=request,
        total_count=total,
        limit=limit,
        offset=offset,
    )
    return {'items': items, 'total': total, 'limit': limit, 'offset': offset}


@router.post('/payouts', status_code=status.HTTP_201_CREATED)
def create_commission_payout(
    body: CommissionPayoutCreate,
    user: dict = Depends(get_current_user),
):
    """
    Creates a new manual or batch commission payout ledger record.
    """
    return default_commission_service.create_payout(body, user_id=user.get('id'))


@router.get('/payouts/{payout_id}')
def get_commission_payout(payout_id: int):
    """
    Retrieves a single commission payout record by ID.
    """
    payout = default_commission_service.get_payout(payout_id)
    if not payout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Commission payout #{payout_id} not found',
        )
    return payout


@router.put('/payouts/{payout_id}')
def update_commission_payout(
    payout_id: int,
    body: CommissionPayoutUpdate,
    user: dict = Depends(get_current_user),
):
    """
    Updates a commission payout record.
    """
    payout = default_commission_service.update_payout(payout_id, body, user_id=user.get('id'))
    if not payout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Commission payout #{payout_id} not found',
        )
    return payout


@router.post('/payouts/{payout_id}/approve')
def approve_commission_payout(
    payout_id: int,
    user: dict = Depends(get_current_user),
):
    """
    Approves a pending commission payout for disbursement.
    """
    payout = default_commission_service.approve_payout(payout_id, user_id=user.get('id'))
    if not payout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Commission payout #{payout_id} not found',
        )
    return payout


@router.post('/payouts/{payout_id}/pay')
def mark_commission_payout_paid(
    payout_id: int,
    payment_date: Optional[date] = Query(None, description='Disbursement date'),
    user: dict = Depends(get_current_user),
):
    """
    Marks an approved commission payout as paid.
    """
    payout = default_commission_service.mark_payout_paid(
        payout_id,
        payment_date=payment_date,
        user_id=user.get('id'),
    )
    if not payout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Commission payout #{payout_id} not found',
        )
    return payout


@router.delete('/payouts/{payout_id}')
def delete_commission_payout(payout_id: int):
    """
    Deletes a commission payout record.
    """
    success = default_commission_service.delete_payout(payout_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Commission payout #{payout_id} not found',
        )
    return {'message': f'Commission payout #{payout_id} deleted successfully', 'success': True}
