import pytest
from pydantic import ValidationError
from modules.inventory.models.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductUOMCreate,
    ProductUOMUpdate,
    ProductUOMResponse,
)


def test_product_create_dual_uom_defaults():
    prod = ProductCreate(
        name="Artisan Cheddar Wheel",
        sku="CHED-001",
    )
    assert prod.is_catch_weight is False
    assert prod.pricing_uom_id is None
    assert prod.nominal_weight is None
    assert prod.tolerance_pct is None
    assert prod.pricing_basis == "weight"


def test_product_create_dual_uom_explicit():
    prod = ProductCreate(
        name="Parmigiano Reggiano Wheel",
        sku="PARM-WHEEL",
        is_catch_weight=True,
        pricing_uom_id=2,  # kg
        nominal_weight=38.5,
        tolerance_pct=10.0,
        pricing_basis="weight",
    )
    assert prod.is_catch_weight is True
    assert prod.pricing_uom_id == 2
    assert prod.nominal_weight == 38.5
    assert prod.tolerance_pct == 10.0
    assert prod.pricing_basis == "weight"


def test_product_create_dual_uom_validation():
    # Negative nominal weight should fail
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Invalid Product",
            sku="INV-001",
            nominal_weight=-5.0,
        )

    # Tolerance > 100 should fail
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Invalid Product",
            sku="INV-002",
            tolerance_pct=150.0,
        )


def test_product_update_dual_uom():
    update = ProductUpdate(
        is_catch_weight=True,
        pricing_uom_id=3,
        nominal_weight=20.0,
        tolerance_pct=5.0,
        pricing_basis="weight",
    )
    dumped = update.model_dump(exclude_unset=True)
    assert dumped == {
        "is_catch_weight": True,
        "pricing_uom_id": 3,
        "nominal_weight": 20.0,
        "tolerance_pct": 5.0,
        "pricing_basis": "weight",
    }


def test_product_response_dual_uom():
    resp = ProductResponse(
        id=10,
        name="Ribeye Primal Cut",
        sku="BEEF-RIB-01",
        type="stockable",
        price=120.0,
        cost_price=80.0,
        tax_rate=0.05,
        weight=15.0,
        volume=0.0,
        is_purchasable=True,
        is_saleable=True,
        is_active=True,
        is_catch_weight=True,
        pricing_uom_id=2,
        nominal_weight=15.0,
        tolerance_pct=7.5,
        pricing_basis="weight",
    )
    assert resp.id == 10
    assert resp.is_catch_weight is True
    assert resp.pricing_uom_id == 2
    assert resp.nominal_weight == 15.0
    assert resp.tolerance_pct == 7.5
    assert resp.pricing_basis == "weight"


def test_product_uom_models_dual_uom():
    uom_create = ProductUOMCreate(
        product_id=10,
        base_uom_id=1,  # Case
        purchase_uom_id=1,
        sales_uom_id=1,
        is_catch_weight=True,
        pricing_uom_id=2,  # kg
        nominal_weight=25.0,
        tolerance_pct=10.0,
        pricing_basis="weight",
    )
    assert uom_create.is_catch_weight is True
    assert uom_create.pricing_uom_id == 2
    assert uom_create.nominal_weight == 25.0
    assert uom_create.tolerance_pct == 10.0

    uom_update = ProductUOMUpdate(
        nominal_weight=26.5,
        tolerance_pct=8.0,
    )
    assert uom_update.nominal_weight == 26.5
    assert uom_update.tolerance_pct == 8.0

    uom_resp = ProductUOMResponse(
        id=1,
        product_id=10,
        base_uom_id=1,
        purchase_factor=1.0,
        sales_factor=1.0,
        is_catch_weight=True,
        pricing_uom_id=2,
        nominal_weight=25.0,
        tolerance_pct=10.0,
        pricing_basis="weight",
    )
    assert uom_resp.is_catch_weight is True
    assert uom_resp.pricing_uom_id == 2
    assert uom_resp.nominal_weight == 25.0
