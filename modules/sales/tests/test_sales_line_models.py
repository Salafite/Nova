import pytest
from pydantic import ValidationError
from modules.sales.models.sales import (
    SalesLineCreate,
    SalesLineUpdate,
    SalesLineResponse,
)


def test_sales_line_create_defaults():
    line = SalesLineCreate(
        sales_order_id=1,
        product_id=10,
        product_name="Parmigiano Reggiano Wheel",
        qty=2.0,
        unit_price=120.0,
        line_total=240.0,
    )
    assert line.sales_order_id == 1
    assert line.product_id == 10
    assert line.product_name == "Parmigiano Reggiano Wheel"
    assert line.qty == 2.0
    assert line.unit_price == 120.0
    assert line.line_total == 240.0
    assert line.is_catch_weight is False
    assert line.pricing_uom_id is None
    assert line.unit_price_pricing_uom is None
    assert line.nominal_weight is None
    assert line.catch_weight_actual is None
    assert line.recalculated_total is None


def test_sales_line_create_explicit_dual_uom():
    line = SalesLineCreate(
        sales_order_id=1,
        product_id=20,
        product_name="Artisan Cheddar Block",
        uom_id=1,  # Case
        qty=5.0,
        unit_price=150.0,
        cost_price=100.0,
        discount=10.0,
        line_total=740.0,
        line_number=1,
        is_catch_weight=True,
        pricing_uom_id=2,  # kg
        unit_price_pricing_uom=15.0,
        nominal_weight=50.0,
        catch_weight_actual=48.5,
        recalculated_total=727.5,
    )
    assert line.is_catch_weight is True
    assert line.pricing_uom_id == 2
    assert line.unit_price_pricing_uom == 15.0
    assert line.nominal_weight == 50.0
    assert line.catch_weight_actual == 48.5
    assert line.recalculated_total == 727.5


def test_sales_line_create_validation():
    # Negative unit_price_pricing_uom should fail
    with pytest.raises(ValidationError):
        SalesLineCreate(
            sales_order_id=1,
            product_name="Invalid Line",
            qty=1.0,
            unit_price=10.0,
            line_total=10.0,
            unit_price_pricing_uom=-5.0,
        )

    # Negative nominal_weight should fail
    with pytest.raises(ValidationError):
        SalesLineCreate(
            sales_order_id=1,
            product_name="Invalid Line",
            qty=1.0,
            unit_price=10.0,
            line_total=10.0,
            nominal_weight=-10.0,
        )

    # Negative catch_weight_actual should fail
    with pytest.raises(ValidationError):
        SalesLineCreate(
            sales_order_id=1,
            product_name="Invalid Line",
            qty=1.0,
            unit_price=10.0,
            line_total=10.0,
            catch_weight_actual=-2.5,
        )

    # Negative recalculated_total should fail
    with pytest.raises(ValidationError):
        SalesLineCreate(
            sales_order_id=1,
            product_name="Invalid Line",
            qty=1.0,
            unit_price=10.0,
            line_total=10.0,
            recalculated_total=-50.0,
        )


def test_sales_line_update_dual_uom():
    update = SalesLineUpdate(
        is_catch_weight=True,
        pricing_uom_id=2,
        unit_price_pricing_uom=14.50,
        nominal_weight=80.0,
        catch_weight_actual=78.2,
        recalculated_total=1133.90,
    )
    dumped = update.model_dump(exclude_unset=True)
    assert dumped == {
        "is_catch_weight": True,
        "pricing_uom_id": 2,
        "unit_price_pricing_uom": 14.50,
        "nominal_weight": 80.0,
        "catch_weight_actual": 78.2,
        "recalculated_total": 1133.90,
    }


def test_sales_line_update_validation():
    # Negative unit_price_pricing_uom
    with pytest.raises(ValidationError):
        SalesLineUpdate(unit_price_pricing_uom=-1.0)

    # Negative nominal_weight
    with pytest.raises(ValidationError):
        SalesLineUpdate(nominal_weight=-1.0)

    # Negative catch_weight_actual
    with pytest.raises(ValidationError):
        SalesLineUpdate(catch_weight_actual=-1.0)

    # Negative recalculated_total
    with pytest.raises(ValidationError):
        SalesLineUpdate(recalculated_total=-1.0)


def test_sales_line_response_dual_uom():
    resp = SalesLineResponse(
        id=101,
        sales_order_id=10,
        product_id=25,
        product_name="Gouda Wheel Aged 20kg",
        uom_id=1,
        qty=2.0,
        unit_price=300.0,
        cost_price=200.0,
        discount=0.0,
        line_total=600.0,
        line_number=1,
        is_catch_weight=True,
        pricing_uom_id=2,
        unit_price_pricing_uom=15.0,
        nominal_weight=40.0,
        catch_weight_actual=41.5,
        recalculated_total=622.5,
    )
    assert resp.id == 101
    assert resp.sales_order_id == 10
    assert resp.is_catch_weight is True
    assert resp.pricing_uom_id == 2
    assert resp.unit_price_pricing_uom == 15.0
    assert resp.nominal_weight == 40.0
    assert resp.catch_weight_actual == 41.5
    assert resp.recalculated_total == 622.5
