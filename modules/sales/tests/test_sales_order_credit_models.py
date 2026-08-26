import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from modules.sales.models.sales import (
    SalesOrderCreate,
    SalesOrderUpdate,
    SalesOrderResponse,
)
from modules.sales.controllers.T0012I import repo as controller_repo
from modules.sales.services.sales_service import ORDER_REPO as service_order_repo


def test_sales_order_create_credit_hold_defaults():
    order = SalesOrderCreate(
        order_number="SO-2026-0001",
        customer_id=1,
    )
    assert order.order_number == "SO-2026-0001"
    assert order.customer_id == 1
    assert order.status == "Pending"
    assert order.hold_reason is None
    assert order.hold_released_by is None
    assert order.hold_released_at is None
    assert order.hold_release_reason is None


def test_sales_order_create_with_credit_hold():
    order = SalesOrderCreate(
        order_number="SO-2026-0002",
        customer_id=2,
        status="Credit Hold",
        hold_reason="Customer credit limit exceeded: Total exposure $12,500.00 > Limit $10,000.00",
    )
    assert order.status == "Credit Hold"
    assert order.hold_reason == "Customer credit limit exceeded: Total exposure $12,500.00 > Limit $10,000.00"
    assert order.hold_released_by is None
    assert order.hold_released_at is None
    assert order.hold_release_reason is None


def test_sales_order_update_credit_hold_release():
    now = datetime.now(timezone.utc)
    update = SalesOrderUpdate(
        status="Pending",
        hold_released_by=5,
        hold_released_at=now,
        hold_release_reason="Approved by Finance Manager - wire transfer received",
    )
    dumped = update.model_dump(exclude_unset=True)
    assert dumped == {
        "status": "Pending",
        "hold_released_by": 5,
        "hold_released_at": now,
        "hold_release_reason": "Approved by Finance Manager - wire transfer received",
    }


def test_sales_order_response_credit_hold_fields():
    now = datetime.now(timezone.utc)
    resp = SalesOrderResponse(
        id=101,
        order_number="SO-2026-0003",
        customer_id=3,
        subtotal=1500.0,
        tax=150.0,
        grand_total=1650.0,
        status="Credit Hold",
        order_date="2026-08-25",
        hold_reason="Customer has 2 invoices overdue by >30 days (total overdue: $4,200.00)",
        hold_released_by=12,
        hold_released_at=now,
        hold_release_reason="Special executive exception granted",
    )
    assert resp.id == 101
    assert resp.status == "Credit Hold"
    assert "invoices overdue" in resp.hold_reason
    assert resp.hold_released_by == 12
    assert resp.hold_released_at == now
    assert resp.hold_release_reason == "Special executive exception granted"


def test_crud_repository_business_columns_contain_credit_hold_fields():
    expected_hold_columns = {
        "hold_reason",
        "hold_released_by",
        "hold_released_at",
        "hold_release_reason",
    }
    assert expected_hold_columns.issubset(set(controller_repo.business_columns))
    assert expected_hold_columns.issubset(set(service_order_repo.business_columns))
