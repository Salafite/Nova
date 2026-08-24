from datetime import datetime, date, timezone
import pytest
from pydantic import ValidationError
from modules.warehouse.models.pick_list import (
    PickListItemCreate,
    PickListItemUpdate,
    PickListItemResponse,
)


def test_pick_list_item_create_defaults():
    item = PickListItemCreate(
        pick_list_id=1,
        product_id=10,
        qty_ordered=5.0,
    )
    assert item.pick_list_id == 1
    assert item.product_id == 10
    assert item.qty_ordered == 5.0
    assert item.qty_picked == 0
    assert item.catch_weight_actual is None
    assert item.catch_weight_uom is None
    assert item.nominal_weight is None
    assert item.tolerance_pct is None
    assert item.tolerance_variance_pct is None
    assert item.tolerance_status == "Not Applicable"
    assert item.supervisor_approved is False
    assert item.supervisor_approved_by is None
    assert item.supervisor_approved_at is None
    assert item.supervisor_notes is None


def test_pick_list_item_create_catch_weight_explicit():
    approved_time = datetime(2026, 8, 23, 10, 0, 0, tzinfo=timezone.utc)
    item = PickListItemCreate(
        pick_list_id=1,
        sales_order_line_id=101,
        product_id=20,
        product_name="Parmigiano Reggiano Wheel",
        qty_ordered=2.0,
        qty_picked=2.0,
        line_number=1,
        catch_weight_actual=78.4,
        catch_weight_uom="kg",
        nominal_weight=80.0,
        tolerance_pct=5.0,
        tolerance_variance_pct=-2.0,
        tolerance_status="Within Tolerance",
        supervisor_approved=True,
        supervisor_approved_by=5,
        supervisor_approved_at=approved_time,
        supervisor_notes="Minor underweight within acceptable range",
    )
    assert item.catch_weight_actual == 78.4
    assert item.catch_weight_uom == "kg"
    assert item.nominal_weight == 80.0
    assert item.tolerance_pct == 5.0
    assert item.tolerance_variance_pct == -2.0
    assert item.tolerance_status == "Within Tolerance"
    assert item.supervisor_approved is True
    assert item.supervisor_approved_by == 5
    assert item.supervisor_approved_at == approved_time
    assert item.supervisor_notes == "Minor underweight within acceptable range"


def test_pick_list_item_create_validation():
    # Negative catch_weight_actual
    with pytest.raises(ValidationError):
        PickListItemCreate(
            pick_list_id=1,
            product_id=10,
            catch_weight_actual=-1.5,
        )

    # Negative nominal_weight
    with pytest.raises(ValidationError):
        PickListItemCreate(
            pick_list_id=1,
            product_id=10,
            nominal_weight=-10.0,
        )

    # tolerance_pct > 100
    with pytest.raises(ValidationError):
        PickListItemCreate(
            pick_list_id=1,
            product_id=10,
            tolerance_pct=150.0,
        )


def test_pick_list_item_update_catch_weight():
    approved_time = datetime(2026, 8, 23, 11, 30, 0, tzinfo=timezone.utc)
    update = PickListItemUpdate(
        qty_picked=1.0,
        catch_weight_actual=41.2,
        catch_weight_uom="kg",
        nominal_weight=38.0,
        tolerance_pct=5.0,
        tolerance_variance_pct=8.42,
        tolerance_status="Approved",
        supervisor_approved=True,
        supervisor_approved_by=3,
        supervisor_approved_at=approved_time,
        supervisor_notes="Approved overweight cheese wheel",
    )
    dumped = update.model_dump(exclude_unset=True)
    assert dumped == {
        "qty_picked": 1.0,
        "catch_weight_actual": 41.2,
        "catch_weight_uom": "kg",
        "nominal_weight": 38.0,
        "tolerance_pct": 5.0,
        "tolerance_variance_pct": 8.42,
        "tolerance_status": "Approved",
        "supervisor_approved": True,
        "supervisor_approved_by": 3,
        "supervisor_approved_at": approved_time,
        "supervisor_notes": "Approved overweight cheese wheel",
    }


def test_pick_list_item_response_catch_weight():
    approved_time = datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc)
    resp = PickListItemResponse(
        id=55,
        pick_list_id=2,
        sales_order_line_id=202,
        product_id=15,
        product_name="Cheddar Block 20kg",
        qty_ordered=3.0,
        qty_picked=3.0,
        line_number=1,
        catch_weight_actual=61.5,
        catch_weight_uom="kg",
        nominal_weight=60.0,
        tolerance_pct=5.0,
        tolerance_variance_pct=2.5,
        tolerance_status="Within Tolerance",
        supervisor_approved=True,
        supervisor_approved_by=2,
        supervisor_approved_at=approved_time,
        supervisor_notes="Scale calibrated",
    )
    assert resp.id == 55
    assert resp.catch_weight_actual == 61.5
    assert resp.catch_weight_uom == "kg"
    assert resp.nominal_weight == 60.0
    assert resp.tolerance_pct == 5.0
    assert resp.tolerance_variance_pct == 2.5
    assert resp.tolerance_status == "Within Tolerance"
    assert resp.supervisor_approved is True
    assert resp.supervisor_approved_by == 2
    assert resp.supervisor_approved_at == approved_time
    assert resp.supervisor_notes == "Scale calibrated"
