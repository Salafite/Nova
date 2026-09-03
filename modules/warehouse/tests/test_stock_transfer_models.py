"""
Unit tests for Stock Transfer and Inter-Branch Replenishment Pydantic models.
"""
from datetime import date, datetime, timezone
import pytest
from pydantic import ValidationError

from modules.warehouse.models.stock_transfer import (
    StockTransferLineCreate,
    StockTransferLineUpdate,
    StockTransferLineResponse,
    StockTransferCreate,
    StockTransferUpdate,
    StockTransferResponse,
    StockTransferDispatchLine,
    StockTransferDispatch,
    StockTransferLossDetail,
    StockTransferReceiveLine,
    StockTransferReceive,
    ReplenishmentSuggestionItem,
    ReplenishmentSuggestionResponse,
    ReplenishmentGenerateItem,
    ReplenishmentGenerateRequest,
    ReplenishmentGenerateResponse,
)
import modules.inventory.models.stock_transfer as inv_stock_transfer
from modules.inventory.models.stock_level import (
    StockLevelCreate,
    StockLevelUpdate,
    StockLevelResponse,
)


def test_stock_transfer_line_create_defaults():
    line = StockTransferLineCreate(
        product_id=10,
        qty_requested=50.0,
    )
    assert line.product_id == 10
    assert line.qty_requested == 50.0
    assert line.qty_dispatched == 0
    assert line.qty_received == 0
    assert line.qty_lost == 0
    assert line.loss_reason is None
    assert line.loss_notes is None
    assert line.batch_id is None
    assert line.batch_number is None
    assert line.line_number == 1
    assert line.is_active is True
    assert line.business_id is None


def test_stock_transfer_line_create_validation():
    # qty_requested must be > 0
    with pytest.raises(ValidationError):
        StockTransferLineCreate(product_id=10, qty_requested=0)

    with pytest.raises(ValidationError):
        StockTransferLineCreate(product_id=10, qty_requested=-5.0)

    # qty_dispatched must be >= 0
    with pytest.raises(ValidationError):
        StockTransferLineCreate(product_id=10, qty_requested=10, qty_dispatched=-1)


def test_stock_transfer_line_update():
    update = StockTransferLineUpdate(
        qty_dispatched=45.0,
        qty_received=40.0,
        qty_lost=5.0,
        loss_reason="Transit Damage",
        loss_notes="Crushed box in transit",
    )
    dumped = update.model_dump(exclude_unset=True)
    assert dumped == {
        "qty_dispatched": 45.0,
        "qty_received": 40.0,
        "qty_lost": 5.0,
        "loss_reason": "Transit Damage",
        "loss_notes": "Crushed box in transit",
    }


def test_stock_transfer_line_response():
    resp = StockTransferLineResponse(
        id=1,
        transfer_id=101,
        product_id=10,
        product_code="PRD-001",
        product_name="Frozen Salmon 1kg",
        uom_name="kg",
        qty_requested=50.0,
        qty_dispatched=50.0,
        qty_received=48.0,
        qty_lost=2.0,
        loss_reason="Transit Damage",
        loss_notes="2 packs damaged",
        batch_id=5,
        batch_number="BAT-2026-001",
        line_number=1,
        notes="Handle with care",
        is_active=True,
        business_id=1,
    )
    assert resp.id == 1
    assert resp.transfer_id == 101
    assert resp.product_code == "PRD-001"
    assert resp.qty_lost == 2.0
    assert resp.loss_reason == "Transit Damage"


def test_stock_transfer_create_defaults_and_nested_lines():
    transfer = StockTransferCreate(
        source_warehouse_id=1,
        destination_warehouse_id=2,
        lines=[
            StockTransferLineCreate(product_id=10, qty_requested=20.0),
            StockTransferLineCreate(product_id=11, qty_requested=15.0),
        ],
    )
    assert transfer.source_warehouse_id == 1
    assert transfer.destination_warehouse_id == 2
    assert transfer.status == "Draft"
    assert transfer.is_active is True
    assert len(transfer.lines) == 2
    assert transfer.lines[0].product_id == 10
    assert transfer.lines[1].product_id == 11


def test_stock_transfer_update():
    now = datetime(2026, 8, 26, 12, 0, 0, tzinfo=timezone.utc)
    update = StockTransferUpdate(
        status="In Transit",
        carrier="FastFreight Logistics",
        tracking_number="TRK-987654321",
        dispatched_at=now,
        dispatched_by=3,
    )
    dumped = update.model_dump(exclude_unset=True)
    assert dumped["status"] == "In Transit"
    assert dumped["carrier"] == "FastFreight Logistics"
    assert dumped["tracking_number"] == "TRK-987654321"
    assert dumped["dispatched_by"] == 3


def test_stock_transfer_response():
    resp = StockTransferResponse(
        id=1,
        transfer_number="TRF-00001",
        source_warehouse_id=1,
        source_warehouse_name="Central Cold Hub",
        destination_warehouse_id=2,
        destination_warehouse_name="Downtown Retail Branch",
        status="In Transit",
        transfer_date=date(2026, 8, 26),
        expected_delivery_date=date(2026, 8, 27),
        carrier="ColdChain Express",
        tracking_number="CCE-10029",
        total_requested_qty=100.0,
        total_dispatched_qty=100.0,
        total_received_qty=0.0,
        total_lost_qty=0.0,
        lines_count=1,
        lines=[
            StockTransferLineResponse(
                id=1,
                transfer_id=1,
                product_id=10,
                qty_requested=100.0,
                qty_dispatched=100.0,
            )
        ],
    )
    assert resp.transfer_number == "TRF-00001"
    assert resp.source_warehouse_name == "Central Cold Hub"
    assert resp.destination_warehouse_name == "Downtown Retail Branch"
    assert len(resp.lines) == 1


def test_stock_transfer_dispatch_and_lines():
    dispatch = StockTransferDispatch(
        carrier="Speedy Express",
        tracking_number="SP-554433",
        dispatched_by=2,
        notes="Dispatched 2 pallets",
        lines=[
            StockTransferDispatchLine(
                line_id=1,
                product_id=10,
                qty_dispatched=50.0,
                batch_number="BAT-001",
            )
        ],
    )
    assert dispatch.carrier == "Speedy Express"
    assert dispatch.tracking_number == "SP-554433"
    assert len(dispatch.lines) == 1
    assert dispatch.lines[0].qty_dispatched == 50.0


def test_stock_transfer_receive_and_losses():
    receipt = StockTransferReceive(
        received_by=4,
        notes="Received with minor transit damage on line 1",
        lines=[
            StockTransferReceiveLine(
                line_id=1,
                product_id=10,
                qty_received=45.0,
                qty_lost=5.0,
                loss_reason="Transit Damage",
                loss_notes="Box was damaged on arrival",
            )
        ],
        losses=[
            StockTransferLossDetail(
                line_id=1,
                product_id=10,
                qty_lost=5.0,
                loss_reason="Transit Damage",
                loss_notes="Box was damaged on arrival",
            )
        ],
    )
    assert receipt.received_by == 4
    assert len(receipt.lines) == 1
    assert receipt.lines[0].qty_received == 45.0
    assert receipt.lines[0].qty_lost == 5.0
    assert len(receipt.losses) == 1
    assert receipt.losses[0].loss_reason == "Transit Damage"


def test_replenishment_suggestion_item_and_response():
    item = ReplenishmentSuggestionItem(
        product_id=10,
        product_code="PRD-010",
        product_name="Organic Milk 1L",
        destination_warehouse_id=3,
        destination_warehouse_name="Branch North",
        current_stock=5.0,
        reserved_stock=1.0,
        in_transit_stock=0.0,
        available_stock=4.0,
        reorder_point=20.0,
        safety_stock=10.0,
        suggested_transfer_qty=30.0,
        source_warehouse_id=1,
        source_warehouse_name="Central Distribution Center",
        source_available_stock=250.0,
        priority="Critical",
        reason="Stock level (4.0) below safety threshold (10.0)",
    )
    assert item.priority == "Critical"
    assert item.suggested_transfer_qty == 30.0

    resp = ReplenishmentSuggestionResponse(
        total_suggestions=1,
        critical_count=1,
        high_count=0,
        items=[item],
        generated_at=datetime.now(timezone.utc),
        business_id=1,
    )
    assert resp.total_suggestions == 1
    assert resp.critical_count == 1
    assert len(resp.items) == 1


def test_replenishment_generate_request_and_response():
    req = ReplenishmentGenerateRequest(
        source_warehouse_id=1,
        destination_warehouse_id=3,
        items=[
            ReplenishmentGenerateItem(
                product_id=10,
                destination_warehouse_id=3,
                source_warehouse_id=1,
                suggested_transfer_qty=30.0,
            )
        ],
        notes="Automated replenishment order",
    )
    assert req.source_warehouse_id == 1
    assert len(req.items) == 1

    resp = ReplenishmentGenerateResponse(
        transfers_created=1,
        transfer_ids=[101],
        transfer_numbers=["TRF-00101"],
    )
    assert resp.transfers_created == 1
    assert resp.transfer_ids == [101]
    assert resp.transfer_numbers == ["TRF-00101"]


def test_inventory_models_reexport():
    assert inv_stock_transfer.StockTransferCreate is StockTransferCreate
    assert inv_stock_transfer.StockTransferResponse is StockTransferResponse
    assert inv_stock_transfer.StockTransferLineCreate is StockTransferLineCreate
    assert inv_stock_transfer.ReplenishmentSuggestionResponse is ReplenishmentSuggestionResponse


def test_stock_level_in_transit_qty():
    sl_create = StockLevelCreate(
        product_id=1,
        warehouse_id=2,
        qty=100.0,
        reserved_qty=10.0,
        in_transit_qty=25.0,
        reorder_level=30.0,
    )
    assert sl_create.in_transit_qty == 25.0

    sl_resp = StockLevelResponse(
        id=1,
        product_id=1,
        warehouse_id=2,
        qty=100.0,
        reserved_qty=10.0,
        in_transit_qty=25.0,
        reorder_level=30.0,
    )
    assert sl_resp.in_transit_qty == 25.0
    assert sl_resp.available_qty == 90.0


def test_tenant_mixin_inheritance():
    from modules.core.models.base import TenantMixin
    from modules.warehouse.models.warehouse import WarehouseCreate, WarehouseUpdate, InventoryCreate, InventoryUpdate

    assert issubclass(StockTransferCreate, TenantMixin)
    assert issubclass(StockTransferUpdate, TenantMixin)
    assert issubclass(StockTransferLineCreate, TenantMixin)
    assert issubclass(StockTransferLineUpdate, TenantMixin)
    assert issubclass(StockTransferResponse, TenantMixin)
    assert issubclass(StockTransferLineResponse, TenantMixin)
    assert issubclass(WarehouseCreate, TenantMixin)
    assert issubclass(WarehouseUpdate, TenantMixin)
    assert issubclass(InventoryCreate, TenantMixin)
    assert issubclass(InventoryUpdate, TenantMixin)

