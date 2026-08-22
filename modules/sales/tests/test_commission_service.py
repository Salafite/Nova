import pytest
from datetime import date
from unittest.mock import MagicMock
from modules.sales.services.commission_service import (
    CommissionService,
    determine_commission_rate,
    calculate_discount_penalty,
)
from modules.sales.models.commission import (
    CommissionRuleCreate,
    CommissionRuleUpdate,
    CommissionPayoutCreate,
    CommissionPayoutUpdate,
)


def test_determine_commission_rate_threshold():
    rule = {
        'base_commission_rate': 6.0,
        'min_margin_threshold': 15.0,
        'tier_rules': [],
    }
    # Below threshold -> 0%
    assert determine_commission_rate(14.9, rule) == 0.0
    assert determine_commission_rate(10.0, rule) == 0.0

    # At or above threshold -> base rate
    assert determine_commission_rate(15.0, rule) == 6.0
    assert determine_commission_rate(25.0, rule) == 6.0


def test_determine_commission_rate_tiered():
    rule = {
        'base_commission_rate': 5.0,
        'min_margin_threshold': 15.0,
        'tier_rules': [
            {'min_margin_pct': 15.0, 'max_margin_pct': 20.0, 'commission_rate': 3.0},
            {'min_margin_pct': 20.0, 'max_margin_pct': 30.0, 'commission_rate': 6.0},
            {'min_margin_pct': 30.0, 'max_margin_pct': None, 'commission_rate': 10.0},
        ],
    }

    # Below all tiers & threshold
    assert determine_commission_rate(12.0, rule) == 0.0

    # Tier 1 (15% - 20%)
    assert determine_commission_rate(15.0, rule) == 3.0
    assert determine_commission_rate(18.5, rule) == 3.0
    assert determine_commission_rate(20.0, rule) == 3.0

    # Tier 2 (20.01% - 30%)
    assert determine_commission_rate(20.1, rule) == 6.0
    assert determine_commission_rate(29.9, rule) == 6.0

    # Tier 3 (30%+)
    assert determine_commission_rate(35.0, rule) == 10.0
    assert determine_commission_rate(50.0, rule) == 10.0


def test_calculate_discount_penalty():
    # 0 discount -> 0 penalty
    assert calculate_discount_penalty(100.0, 0.0, 0.50) == 0.0

    # 10% discount with 0.5 penalty rate:
    # 100 * (10 * 0.5 / 100) = 100 * 0.05 = 5.0
    assert calculate_discount_penalty(100.0, 10.0, 0.50) == 5.0

    # 20% discount with 1.0 penalty rate:
    # 200 * (20 * 1.0 / 100) = 40.0
    assert calculate_discount_penalty(200.0, 20.0, 1.0) == 40.0

    # Penalty should not exceed gross commission
    assert calculate_discount_penalty(50.0, 100.0, 2.0) == 50.0


def test_commission_service_calculate_statement():
    mock_repo = MagicMock()
    mock_repo.get_sales_rep_info.return_value = {
        'id': 101,
        'username': 'jdoe',
        'full_name': 'John Doe',
        'email': 'john.doe@company.com',
    }
    mock_repo.get_active_rule_for_rep.return_value = {
        'id': 1,
        'rule_name': 'Standard 5% Margin Plan',
        'sales_rep_id': 101,
        'base_commission_rate': 5.0,
        'min_margin_threshold': 15.0,
        'tier_rules': [],
        'discount_penalty_rate': 0.50,
    }

    mock_repo.get_sales_rep_invoices_and_payments.return_value = [
        # 1. Fully collected, high margin (30%), no discount
        {
            'invoice_id': 1,
            'invoice_number': 'INV-001',
            'order_id': 10,
            'order_number': 'SO-001',
            'customer_id': 50,
            'customer_name': 'Grand Hotel',
            'gross_sales': 1000.0,
            'discount_amount': 0.0,
            'cogs': 650.0,
            'freight_cost': 50.0,
            'invoice_total': 1000.0,
            'collected_cash': 1000.0,
            'latest_payment_id': 201,
            'latest_payment_date': date(2026, 8, 15),
            'payout_status': None,
        },
        # 2. Partially collected, margin 25%, with discount granted
        {
            'invoice_id': 2,
            'invoice_number': 'INV-002',
            'order_id': 11,
            'order_number': 'SO-002',
            'customer_id': 51,
            'customer_name': 'Bistro Cafe',
            'gross_sales': 2000.0,
            'discount_amount': 200.0,  # 10% discount
            'cogs': 1200.0,
            'freight_cost': 150.0,
            'invoice_total': 1800.0,
            'collected_cash': 900.0,  # 50% collected
            'latest_payment_id': 202,
            'latest_payment_date': date(2026, 8, 18),
            'payout_status': None,
        },
        # 3. Unpaid (0 collected cash)
        {
            'invoice_id': 3,
            'invoice_number': 'INV-003',
            'order_id': 12,
            'order_number': 'SO-003',
            'customer_id': 52,
            'customer_name': 'Seaside Grill',
            'gross_sales': 500.0,
            'discount_amount': 0.0,
            'cogs': 300.0,
            'freight_cost': 50.0,
            'invoice_total': 500.0,
            'collected_cash': 0.0,
            'latest_payment_id': None,
            'latest_payment_date': None,
            'payout_status': None,
        },
        # 4. Low margin (<15% threshold: net revenue 1000, cogs 900 -> margin 10%)
        {
            'invoice_id': 4,
            'invoice_number': 'INV-004',
            'order_id': 13,
            'order_number': 'SO-004',
            'customer_id': 53,
            'customer_name': 'Budget Diner',
            'gross_sales': 1000.0,
            'discount_amount': 0.0,
            'cogs': 900.0,
            'freight_cost': 0.0,
            'invoice_total': 1000.0,
            'collected_cash': 1000.0,
            'latest_payment_id': 204,
            'latest_payment_date': date(2026, 8, 20),
            'payout_status': None,
        },
    ]

    service = CommissionService(repo=mock_repo)
    stmt = service.calculate_statement(sales_rep_id=101)

    assert stmt.sales_rep_id == 101
    assert stmt.sales_rep_name == 'John Doe'
    assert len(stmt.items) == 4

    # Item 1: gross_profit = 1000 - 650 - 50 = 300. margin% = 30%.
    # realized_margin = 300. rate = 5%. gross_comm = 15.0. discount penalty = 0. net_comm = 15.0. status = 'Collected'
    item1 = stmt.items[0]
    assert item1.realized_gross_margin == 300.0
    assert item1.realized_margin_pct == 30.0
    assert item1.commission_rate == 5.0
    assert item1.gross_commission == 15.0
    assert item1.discount_penalty == 0.0
    assert item1.net_commission == 15.0
    assert item1.status == 'Collected'

    # Item 2: net_rev = 1800. gross_profit = 1800 - 1200 - 150 = 450. margin% = 25%.
    # 50% collected -> realized_gross_margin = 225.0.
    # rate = 5%. gross_comm = 225 * 0.05 = 11.25.
    # discount_pct = 200 / 2000 * 100 = 10%. penalty_rate = 0.50. penalty = 11.25 * (10 * 0.5 / 100) = 0.56.
    # net_comm = 11.25 - 0.56 = 10.69. status = 'Partial'
    item2 = stmt.items[1]
    assert item2.realized_gross_margin == 225.0
    assert item2.realized_margin_pct == 25.0
    assert item2.gross_commission == 11.25
    assert item2.discount_penalty == 0.56
    assert item2.net_commission == 10.69
    assert item2.status == 'Partial'

    # Item 3: 0 collected cash -> 0 realized margin & 0 commission
    item3 = stmt.items[2]
    assert item3.collected_cash == 0.0
    assert item3.realized_gross_margin == 0.0
    assert item3.gross_commission == 0.0
    assert item3.net_commission == 0.0
    assert item3.status == 'Pending'

    # Item 4: margin% = 10% (<15% threshold) -> 0% commission rate & 0 commission
    item4 = stmt.items[3]
    assert item4.realized_margin_pct == 10.0
    assert item4.commission_rate == 0.0
    assert item4.gross_commission == 0.0
    assert item4.net_commission == 0.0

    # Summary aggregations
    assert stmt.total_booked_sales == 4300.0
    assert stmt.total_collected_amount == 2900.0
    assert stmt.total_realized_gross_margin == 625.0
    assert stmt.gross_commission_earned == 26.25
    assert stmt.total_discount_penalties == 0.56
    assert stmt.net_commission_payable == 25.69
    assert stmt.pending_commission_amount == 25.69


def test_commission_service_summaries_and_payouts():
    mock_repo = MagicMock()
    mock_repo.list_all_sales_reps.return_value = [
        {'id': 101, 'full_name': 'Rep A', 'email': 'a@company.com'},
        {'id': 102, 'full_name': 'Rep B', 'email': 'b@company.com'},
    ]
    mock_repo.get_sales_rep_info.side_effect = lambda rep_id, conn=None: {
        'id': rep_id,
        'full_name': f'Rep {rep_id}',
        'email': f'{rep_id}@company.com',
    }
    mock_repo.get_active_rule_for_rep.return_value = {
        'base_commission_rate': 5.0,
        'min_margin_threshold': 15.0,
        'tier_rules': [],
        'discount_penalty_rate': 0.50,
    }
    mock_repo.get_sales_rep_invoices_and_payments.return_value = [
        {
            'invoice_id': 10,
            'invoice_number': 'INV-10',
            'gross_sales': 1000.0,
            'discount_amount': 0.0,
            'cogs': 700.0,
            'freight_cost': 0.0,
            'invoice_total': 1000.0,
            'collected_cash': 1000.0,
            'latest_payment_id': 500,
            'latest_payment_date': date(2026, 8, 1),
            'payout_status': None,
        }
    ]
    mock_repo.create_payout.return_value = {
        'id': 1,
        'payout_number': 'PAY-101-10-ABCDEF',
        'sales_rep_id': 101,
        'net_commission_amount': 15.0,
        'status': 'Pending',
    }

    service = CommissionService(repo=mock_repo)

    # Test Summaries
    summaries = service.get_commission_summaries()
    assert len(summaries) == 2
    assert summaries[0].sales_rep_id in (101, 102)

    # Test Payout Generation
    payouts = service.generate_payouts(sales_rep_id=101)
    assert len(payouts) == 1
    assert payouts[0]['payout_number'] == 'PAY-101-10-ABCDEF'
    mock_repo.create_payout.assert_called_once()


def test_commission_service_rule_crud():
    mock_repo = MagicMock()
    service = CommissionService(repo=mock_repo)

    # Create rule
    rule_in = CommissionRuleCreate(
        rule_name='Gold Rep Plan',
        sales_rep_id=101,
        base_commission_rate=8.0,
        min_margin_threshold=20.0,
        tier_rules=[{'min_margin_pct': 20.0, 'commission_rate': 8.0}],
        discount_penalty_rate=0.75,
    )
    mock_repo.create_rule.return_value = {'id': 5, **rule_in.model_dump()}

    created = service.create_rule(rule_in, user_id=1)
    assert created['id'] == 5
    assert created['rule_name'] == 'Gold Rep Plan'
    mock_repo.create_rule.assert_called_once()

    # Update rule
    rule_up = CommissionRuleUpdate(base_commission_rate=9.0)
    mock_repo.update_rule.return_value = {'id': 5, 'base_commission_rate': 9.0}
    updated = service.update_rule(5, rule_up, user_id=1)
    assert updated['base_commission_rate'] == 9.0

    # Delete rule
    mock_repo.delete_rule.return_value = True
    assert service.delete_rule(5) is True


def test_commission_service_payout_crud_and_transitions():
    mock_repo = MagicMock()
    service = CommissionService(repo=mock_repo)

    payout_in = CommissionPayoutCreate(
        sales_rep_id=101,
        invoice_id=10,
        collected_amount=1000.0,
        realized_gross_margin=300.0,
        commission_rate=5.0,
        commission_amount=15.0,
        discount_penalty=0.0,
        net_commission_amount=15.0,
    )
    mock_repo.create_payout.return_value = {'id': 20, **payout_in.model_dump(), 'status': 'Pending'}
    created = service.create_payout(payout_in, user_id=1)
    assert created['id'] == 20
    assert created['status'] == 'Pending'

    # Approve payout
    mock_repo.update_payout.return_value = {'id': 20, 'status': 'Approved'}
    approved = service.approve_payout(20, user_id=1)
    assert approved['status'] == 'Approved'

    # Mark paid
    mock_repo.update_payout.return_value = {'id': 20, 'status': 'Paid', 'payment_date': date(2026, 8, 22)}
    paid = service.mark_payout_paid(20, payment_date=date(2026, 8, 22), user_id=1)
    assert paid['status'] == 'Paid'
    assert paid['payment_date'] == date(2026, 8, 22)
