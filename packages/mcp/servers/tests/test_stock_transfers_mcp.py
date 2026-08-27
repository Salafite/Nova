import pytest
from unittest.mock import patch, MagicMock
from packages.mcp.server import McpServer
from packages.mcp.registry import (
    call_tool,
    read_resource,
    get_tools,
    list_resources,
    _tools,
    _resources,
    _prompts,
)
from packages.mcp.servers import warehouse_mcp, inventory_mcp
from modules.core.context import get_current_tenant


MOCK_TRANSFER = {
    "id": 1,
    "transfer_number": "TRF-20260826-0001",
    "source_warehouse_id": 1,
    "destination_warehouse_id": 2,
    "source_warehouse_name": "Central Hub",
    "destination_warehouse_name": "North Branch",
    "status": "Draft",
    "total_requested_qty": 100.0,
    "total_dispatched_qty": 0.0,
    "total_received_qty": 0.0,
    "total_lost_qty": 0.0,
    "lines": [
        {
            "id": 10,
            "stock_transfer_id": 1,
            "product_id": 101,
            "product_name": "Whole Milk 1L",
            "qty_requested": 100.0,
            "qty_dispatched": 0.0,
            "qty_received": 0.0,
            "qty_lost": 0.0,
        }
    ],
}

MOCK_DISPATCHED_TRANSFER = {
    "id": 1,
    "transfer_number": "TRF-20260826-0001",
    "source_warehouse_id": 1,
    "destination_warehouse_id": 2,
    "status": "In Transit",
    "carrier": "ColdExpress",
    "tracking_number": "TRK-987654",
    "dispatched_by": 5,
    "total_requested_qty": 100.0,
    "total_dispatched_qty": 100.0,
    "total_received_qty": 0.0,
    "total_lost_qty": 0.0,
}

MOCK_RECEIVED_TRANSFER = {
    "id": 1,
    "transfer_number": "TRF-20260826-0001",
    "source_warehouse_id": 1,
    "destination_warehouse_id": 2,
    "status": "Received",
    "received_by": 6,
    "total_requested_qty": 100.0,
    "total_dispatched_qty": 100.0,
    "total_received_qty": 98.0,
    "total_lost_qty": 2.0,
    "lines": [
        {
            "id": 10,
            "product_id": 101,
            "qty_requested": 100.0,
            "qty_dispatched": 100.0,
            "qty_received": 98.0,
            "qty_lost": 2.0,
            "loss_reason": "Transit Damage",
            "loss_notes": "2 cartons crushed in transit",
        }
    ],
}

MOCK_REPLENISHMENT_SUGGESTIONS = {
    "total_suggestions": 2,
    "critical_count": 1,
    "high_count": 1,
    "items": [
        {
            "product_id": 101,
            "product_name": "Whole Milk 1L",
            "product_sku": "DRY-MLK-001",
            "destination_warehouse_id": 2,
            "destination_warehouse_name": "North Branch",
            "source_warehouse_id": 1,
            "source_warehouse_name": "Central Hub",
            "current_stock": 5.0,
            "in_transit_stock": 0.0,
            "effective_stock": 5.0,
            "reorder_level": 50.0,
            "safety_stock": 25.0,
            "deficit_qty": 45.0,
            "suggested_transfer_qty": 70.0,
            "priority": "Critical",
            "source_available_stock": 500.0,
        },
        {
            "product_id": 102,
            "product_name": "Cheddar Cheese 500g",
            "product_sku": "DRY-CHD-002",
            "destination_warehouse_id": 2,
            "destination_warehouse_name": "North Branch",
            "source_warehouse_id": 1,
            "source_warehouse_name": "Central Hub",
            "current_stock": 18.0,
            "in_transit_stock": 0.0,
            "effective_stock": 18.0,
            "reorder_level": 30.0,
            "safety_stock": 15.0,
            "deficit_qty": 12.0,
            "suggested_transfer_qty": 27.0,
            "priority": "High",
            "source_available_stock": 200.0,
        },
    ],
}

MOCK_GENERATE_TRANSFERS_RESULT = {
    "transfers_created": 1,
    "transfer_ids": [1],
    "transfer_numbers": ["TRF-20260826-0001"],
    "transfers": [
        {
            "id": 1,
            "transfer_number": "TRF-20260826-0001",
            "source_warehouse_id": 1,
            "destination_warehouse_id": 2,
            "status": "Draft",
            "line_count": 2,
            "total_requested_qty": 97.0,
        }
    ],
}


def _req(method: str, params: dict = None, req_id: int = 1):
    msg = {"jsonrpc": "2.0", "method": method, "id": req_id}
    if params is not None:
        msg["params"] = params
    return msg


@pytest.fixture(autouse=True)
def clean_registry():
    _tools.clear()
    _resources.clear()
    _prompts.clear()
    yield
    _tools.clear()
    _resources.clear()
    _prompts.clear()


class TestWarehouseMcpStockTransfers:
    """Test warehouse MCP server stock transfer tool registration and execution."""

    def test_tool_registration(self):
        warehouse_mcp.register_tools()
        tools = {t.name: t for t in get_tools()}

        assert "list_stock_transfers" in tools
        assert "get_stock_transfer" in tools
        assert "create_stock_transfer" in tools
        assert "dispatch_stock_transfer" in tools
        assert "receive_stock_transfer" in tools

        # Validate create_stock_transfer schema
        create_schema = tools["create_stock_transfer"].input_schema
        assert "source_warehouse_id" in create_schema["properties"]
        assert "destination_warehouse_id" in create_schema["properties"]
        assert "lines" in create_schema["properties"]
        assert "source_warehouse_id" in create_schema["required"]
        assert "destination_warehouse_id" in create_schema["required"]
        assert "lines" in create_schema["required"]

        # Validate dispatch_stock_transfer schema
        dispatch_schema = tools["dispatch_stock_transfer"].input_schema
        assert "id" in dispatch_schema["properties"]
        assert "carrier" in dispatch_schema["properties"]
        assert "tracking_number" in dispatch_schema["properties"]
        assert "dispatched_by" in dispatch_schema["properties"]
        assert "lines" in dispatch_schema["properties"]

        # Validate receive_stock_transfer schema
        receive_schema = tools["receive_stock_transfer"].input_schema
        assert "id" in receive_schema["properties"]
        assert "received_by" in receive_schema["properties"]
        assert "lines" in receive_schema["properties"]
        assert "losses" in receive_schema["properties"]

        # Validate resource registration
        resources = {r.uri: r for r in list_resources()}
        assert "nova://warehouse/stock-transfers" in resources

    def test_list_stock_transfers(self):
        warehouse_mcp.register_tools()
        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.list_with_lines.return_value = [MOCK_TRANSFER]
            result = call_tool(
                "list_stock_transfers",
                {"status": "Draft", "source_warehouse_id": 1, "destination_warehouse_id": 2, "limit": 20, "offset": 0},
            )
            assert result == [MOCK_TRANSFER]
            mock_svc.list_with_lines.assert_called_once_with(
                filters={"status": "Draft", "source_warehouse_id": 1, "destination_warehouse_id": 2},
                limit=20,
                offset=0,
            )

    def test_get_stock_transfer(self):
        warehouse_mcp.register_tools()
        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.get_transfer_with_lines.return_value = MOCK_TRANSFER
            result = call_tool("get_stock_transfer", {"id": 1})
            assert result == MOCK_TRANSFER
            mock_svc.get_transfer_with_lines.assert_called_once_with(1)

    def test_create_stock_transfer_with_lines(self):
        warehouse_mcp.register_tools()
        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.create_transfer.return_value = MOCK_TRANSFER
            lines = [{"product_id": 101, "qty_requested": 100.0, "batch_number": "LOT-001"}]
            result = call_tool(
                "create_stock_transfer",
                {
                    "source_warehouse_id": 1,
                    "destination_warehouse_id": 2,
                    "lines": lines,
                    "carrier": "ColdExpress",
                    "tracking_number": "TRK-987654",
                    "notes": "Urgent branch replenishment",
                    "transfer_date": "2026-08-26",
                    "expected_delivery_date": "2026-08-28",
                },
            )
            assert result == MOCK_TRANSFER
            mock_svc.create_transfer.assert_called_once_with({
                "source_warehouse_id": 1,
                "destination_warehouse_id": 2,
                "lines": lines,
                "carrier": "ColdExpress",
                "tracking_number": "TRK-987654",
                "notes": "Urgent branch replenishment",
                "transfer_date": "2026-08-26",
                "expected_delivery_date": "2026-08-28",
            })

    def test_create_stock_transfer_with_items_alias(self):
        warehouse_mcp.register_tools()
        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.create_transfer.return_value = MOCK_TRANSFER
            items = [{"product_id": 101, "qty_requested": 50.0}]
            result = warehouse_mcp._create_stock_transfer(
                source_warehouse_id=1,
                destination_warehouse_id=2,
                items=items,
            )
            assert result == MOCK_TRANSFER
            mock_svc.create_transfer.assert_called_once_with({
                "source_warehouse_id": 1,
                "destination_warehouse_id": 2,
                "lines": items,
            })

    def test_dispatch_stock_transfer(self):
        warehouse_mcp.register_tools()
        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.dispatch_transfer.return_value = MOCK_DISPATCHED_TRANSFER
            dispatch_lines = [{"line_id": 10, "qty_dispatched": 100.0, "batch_number": "LOT-001"}]
            result = call_tool(
                "dispatch_stock_transfer",
                {
                    "id": 1,
                    "carrier": "ColdExpress",
                    "tracking_number": "TRK-987654",
                    "dispatched_by": 5,
                    "dispatched_at": "2026-08-26T10:00:00Z",
                    "notes": "Loaded into refrigerated truck",
                    "lines": dispatch_lines,
                },
            )
            assert result == MOCK_DISPATCHED_TRANSFER
            mock_svc.dispatch_transfer.assert_called_once_with(
                1,
                dispatch_data={
                    "carrier": "ColdExpress",
                    "tracking_number": "TRK-987654",
                    "dispatched_by": 5,
                    "dispatched_at": "2026-08-26T10:00:00Z",
                    "notes": "Loaded into refrigerated truck",
                    "lines": dispatch_lines,
                },
            )

    def test_dispatch_stock_transfer_transfer_id_alias(self):
        warehouse_mcp.register_tools()
        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.dispatch_transfer.return_value = MOCK_DISPATCHED_TRANSFER
            result = call_tool("dispatch_stock_transfer", {"transfer_id": 1, "carrier": "ColdExpress"})
            assert result == MOCK_DISPATCHED_TRANSFER
            mock_svc.dispatch_transfer.assert_called_once_with(1, dispatch_data={"carrier": "ColdExpress"})

    def test_dispatch_stock_transfer_missing_id_raises_error(self):
        warehouse_mcp.register_tools()
        with pytest.raises(ValueError, match="Transfer ID .* is required"):
            warehouse_mcp._dispatch_stock_transfer(carrier="ColdExpress")

    def test_receive_stock_transfer(self):
        warehouse_mcp.register_tools()
        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.receive_transfer.return_value = MOCK_RECEIVED_TRANSFER
            receive_lines = [
                {
                    "line_id": 10,
                    "qty_received": 98.0,
                    "qty_lost": 2.0,
                    "loss_reason": "Transit Damage",
                    "loss_notes": "2 cartons crushed in transit",
                }
            ]
            losses = [
                {
                    "line_id": 10,
                    "product_id": 101,
                    "qty_lost": 2.0,
                    "loss_reason": "Transit Damage",
                    "loss_notes": "Crushed boxes",
                }
            ]
            result = call_tool(
                "receive_stock_transfer",
                {
                    "id": 1,
                    "received_by": 6,
                    "received_at": "2026-08-26T14:30:00Z",
                    "notes": "Verified receipt with minor damage",
                    "lines": receive_lines,
                    "losses": losses,
                },
            )
            assert result == MOCK_RECEIVED_TRANSFER
            mock_svc.receive_transfer.assert_called_once_with(
                1,
                receive_data={
                    "received_by": 6,
                    "received_at": "2026-08-26T14:30:00Z",
                    "notes": "Verified receipt with minor damage",
                    "lines": receive_lines,
                    "losses": losses,
                },
            )

    def test_receive_stock_transfer_transfer_id_alias(self):
        warehouse_mcp.register_tools()
        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.receive_transfer.return_value = MOCK_RECEIVED_TRANSFER
            result = call_tool("receive_stock_transfer", {"transfer_id": 1, "received_by": 6})
            assert result == MOCK_RECEIVED_TRANSFER
            mock_svc.receive_transfer.assert_called_once_with(1, receive_data={"received_by": 6})

    def test_receive_stock_transfer_missing_id_raises_error(self):
        warehouse_mcp.register_tools()
        with pytest.raises(ValueError, match="Transfer ID .* is required"):
            warehouse_mcp._receive_stock_transfer(received_by=6)

    def test_read_stock_transfers_resource(self):
        warehouse_mcp.register_tools()
        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.list_with_lines.return_value = [MOCK_TRANSFER]
            result = read_resource("nova://warehouse/stock-transfers")
            assert result == [MOCK_TRANSFER]


class TestInventoryMcpReplenishment:
    """Test inventory MCP server replenishment tool registration and execution."""

    def test_tool_registration(self):
        inventory_mcp.register_tools()
        tools = {t.name: t for t in get_tools()}

        assert "list_replenishment_suggestions" in tools
        assert "generate_replenishment_transfers" in tools

        # Validate list_replenishment_suggestions schema
        list_schema = tools["list_replenishment_suggestions"].input_schema
        assert "warehouse_id" in list_schema["properties"]
        assert "destination_warehouse_id" in list_schema["properties"]
        assert "source_warehouse_id" in list_schema["properties"]
        assert "product_id" in list_schema["properties"]
        assert "category" in list_schema["properties"]
        assert "priority" in list_schema["properties"]
        assert "min_deficit" in list_schema["properties"]
        assert "safety_stock_ratio" in list_schema["properties"]
        assert "target_coverage_multiplier" in list_schema["properties"]

        # Validate generate_replenishment_transfers schema
        gen_schema = tools["generate_replenishment_transfers"].input_schema
        assert "destination_warehouse_id" in gen_schema["properties"]
        assert "source_warehouse_id" in gen_schema["properties"]
        assert "items" in gen_schema["properties"]
        assert "carrier" in gen_schema["properties"]
        assert "notes" in gen_schema["properties"]

        # Validate resource registration
        resources = {r.uri: r for r in list_resources()}
        assert "nova://inventory/replenishment-suggestions" in resources

    def test_list_replenishment_suggestions_default(self):
        inventory_mcp.register_tools()
        with patch.object(inventory_mcp, "_replenishment_svc", MagicMock()) as mock_svc:
            mock_svc.get_replenishment_suggestions.return_value = MOCK_REPLENISHMENT_SUGGESTIONS
            result = call_tool("list_replenishment_suggestions", {})
            assert result == MOCK_REPLENISHMENT_SUGGESTIONS
            mock_svc.get_replenishment_suggestions.assert_called_once_with(
                warehouse_id=None,
                source_warehouse_id=None,
                product_id=None,
                category=None,
                priority=None,
                min_deficit=0.0,
                safety_stock_ratio=0.5,
                target_coverage_multiplier=1.5,
            )

    def test_list_replenishment_suggestions_with_filters(self):
        inventory_mcp.register_tools()
        with patch.object(inventory_mcp, "_replenishment_svc", MagicMock()) as mock_svc:
            mock_svc.get_replenishment_suggestions.return_value = MOCK_REPLENISHMENT_SUGGESTIONS
            result = call_tool(
                "list_replenishment_suggestions",
                {
                    "warehouse_id": 2,
                    "source_warehouse_id": 1,
                    "product_id": 101,
                    "category": "Dairy",
                    "priority": "Critical",
                    "min_deficit": 10.0,
                    "safety_stock_ratio": 0.6,
                    "target_coverage_multiplier": 2.0,
                },
            )
            assert result == MOCK_REPLENISHMENT_SUGGESTIONS
            mock_svc.get_replenishment_suggestions.assert_called_once_with(
                warehouse_id=2,
                source_warehouse_id=1,
                product_id=101,
                category="Dairy",
                priority="Critical",
                min_deficit=10.0,
                safety_stock_ratio=0.6,
                target_coverage_multiplier=2.0,
            )

    def test_list_replenishment_suggestions_destination_warehouse_id_alias(self):
        inventory_mcp.register_tools()
        with patch.object(inventory_mcp, "_replenishment_svc", MagicMock()) as mock_svc:
            mock_svc.get_replenishment_suggestions.return_value = MOCK_REPLENISHMENT_SUGGESTIONS
            result = call_tool("list_replenishment_suggestions", {"destination_warehouse_id": 3})
            assert result == MOCK_REPLENISHMENT_SUGGESTIONS
            mock_svc.get_replenishment_suggestions.assert_called_once_with(
                warehouse_id=3,
                source_warehouse_id=None,
                product_id=None,
                category=None,
                priority=None,
                min_deficit=0.0,
                safety_stock_ratio=0.5,
                target_coverage_multiplier=1.5,
            )

    def test_generate_replenishment_transfers(self):
        inventory_mcp.register_tools()
        with patch.object(inventory_mcp, "_replenishment_svc", MagicMock()) as mock_svc:
            mock_svc.generate_transfers.return_value = MOCK_GENERATE_TRANSFERS_RESULT
            items = [
                {
                    "product_id": 101,
                    "destination_warehouse_id": 2,
                    "source_warehouse_id": 1,
                    "suggested_transfer_qty": 70.0,
                },
                {
                    "product_id": 102,
                    "destination_warehouse_id": 2,
                    "source_warehouse_id": 1,
                    "suggested_transfer_qty": 27.0,
                },
            ]
            result = call_tool(
                "generate_replenishment_transfers",
                {
                    "destination_warehouse_id": 2,
                    "source_warehouse_id": 1,
                    "items": items,
                    "transfer_date": "2026-08-26",
                    "expected_delivery_date": "2026-08-28",
                    "carrier": "ColdExpress",
                    "notes": "Automated replenishment batch",
                },
            )
            assert result == MOCK_GENERATE_TRANSFERS_RESULT
            mock_svc.generate_transfers.assert_called_once_with(
                payload={
                    "destination_warehouse_id": 2,
                    "source_warehouse_id": 1,
                    "items": items,
                    "transfer_date": "2026-08-26",
                    "expected_delivery_date": "2026-08-28",
                    "carrier": "ColdExpress",
                    "notes": "Automated replenishment batch",
                },
                user_id=None,
            )

    def test_generate_replenishment_transfers_with_user_context(self):
        inventory_mcp.register_tools()
        with patch.object(inventory_mcp, "_replenishment_svc", MagicMock()) as mock_svc:
            mock_svc.generate_transfers.return_value = MOCK_GENERATE_TRANSFERS_RESULT
            user = {"id": 8, "username": "logistics_mgr", "business_id": 42}
            result = call_tool(
                "generate_replenishment_transfers",
                {"destination_warehouse_id": 2},
                user=user,
            )
            assert result == MOCK_GENERATE_TRANSFERS_RESULT
            mock_svc.generate_transfers.assert_called_once_with(
                payload={
                    "destination_warehouse_id": 2,
                    "source_warehouse_id": None,
                    "items": None,
                    "transfer_date": None,
                    "expected_delivery_date": None,
                    "carrier": None,
                    "notes": None,
                },
                user_id=8,
            )

    def test_generate_replenishment_transfers_suggestions_alias(self):
        inventory_mcp.register_tools()
        with patch.object(inventory_mcp, "_replenishment_svc", MagicMock()) as mock_svc:
            mock_svc.generate_transfers.return_value = MOCK_GENERATE_TRANSFERS_RESULT
            suggestions = [
                {"product_id": 101, "destination_warehouse_id": 2, "source_warehouse_id": 1, "suggested_transfer_qty": 70.0}
            ]
            result = inventory_mcp._generate_replenishment_transfers(suggestions=suggestions)
            assert result == MOCK_GENERATE_TRANSFERS_RESULT
            mock_svc.generate_transfers.assert_called_once_with(
                payload={
                    "destination_warehouse_id": None,
                    "source_warehouse_id": None,
                    "items": suggestions,
                    "transfer_date": None,
                    "expected_delivery_date": None,
                    "carrier": None,
                    "notes": None,
                },
                user_id=None,
            )

    def test_read_replenishment_suggestions_resource(self):
        inventory_mcp.register_tools()
        with patch.object(inventory_mcp, "_replenishment_svc", MagicMock()) as mock_svc:
            mock_svc.get_replenishment_suggestions.return_value = MOCK_REPLENISHMENT_SUGGESTIONS
            result = read_resource("nova://inventory/replenishment-suggestions")
            assert result == MOCK_REPLENISHMENT_SUGGESTIONS


class TestMcpServerJsonRpcIntegration:
    """Test full MCP Server JSON-RPC protocol integration for stock transfers and replenishment."""

    def setup_method(self):
        _tools.clear()
        _resources.clear()
        _prompts.clear()
        self.server = McpServer(name="StockTransferIntegrationTest", version="1.0")
        warehouse_mcp.register_tools()
        inventory_mcp.register_tools()

    def test_jsonrpc_tools_list_contains_stock_transfers_and_replenishment(self):
        resp = self.server.handle_request(_req("tools/list"))
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]

        assert "list_stock_transfers" in tool_names
        assert "get_stock_transfer" in tool_names
        assert "create_stock_transfer" in tool_names
        assert "dispatch_stock_transfer" in tool_names
        assert "receive_stock_transfer" in tool_names
        assert "list_replenishment_suggestions" in tool_names
        assert "generate_replenishment_transfers" in tool_names

    def test_jsonrpc_resources_list(self):
        resp = self.server.handle_request(_req("resources/list"))
        assert resp["jsonrpc"] == "2.0"
        uris = [r["uri"] for r in resp["result"]["resources"]]
        assert "nova://warehouse/stock-transfers" in uris
        assert "nova://inventory/replenishment-suggestions" in uris

    def test_jsonrpc_call_create_stock_transfer(self):
        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.create_transfer.return_value = MOCK_TRANSFER
            resp = self.server.handle_request(_req("tools/call", {
                "name": "create_stock_transfer",
                "arguments": {
                    "source_warehouse_id": 1,
                    "destination_warehouse_id": 2,
                    "lines": [{"product_id": 101, "qty_requested": 100.0}],
                    "carrier": "ColdExpress",
                },
            }))
        assert resp["jsonrpc"] == "2.0"
        content = resp["result"]["content"][0]["text"]
        assert "TRF-20260826-0001" in content
        assert "Draft" in content

    def test_jsonrpc_call_dispatch_stock_transfer(self):
        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.dispatch_transfer.return_value = MOCK_DISPATCHED_TRANSFER
            resp = self.server.handle_request(_req("tools/call", {
                "name": "dispatch_stock_transfer",
                "arguments": {
                    "id": 1,
                    "carrier": "ColdExpress",
                    "tracking_number": "TRK-987654",
                },
            }))
        assert resp["jsonrpc"] == "2.0"
        content = resp["result"]["content"][0]["text"]
        assert "In Transit" in content
        assert "ColdExpress" in content

    def test_jsonrpc_call_receive_stock_transfer(self):
        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.receive_transfer.return_value = MOCK_RECEIVED_TRANSFER
            resp = self.server.handle_request(_req("tools/call", {
                "name": "receive_stock_transfer",
                "arguments": {
                    "id": 1,
                    "received_by": 6,
                    "lines": [{"line_id": 10, "qty_received": 98.0, "qty_lost": 2.0, "loss_reason": "Transit Damage"}],
                },
            }))
        assert resp["jsonrpc"] == "2.0"
        content = resp["result"]["content"][0]["text"]
        assert "Received" in content
        assert "Transit Damage" in content

    def test_jsonrpc_call_list_replenishment_suggestions(self):
        with patch.object(inventory_mcp, "_replenishment_svc", MagicMock()) as mock_svc:
            mock_svc.get_replenishment_suggestions.return_value = MOCK_REPLENISHMENT_SUGGESTIONS
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_replenishment_suggestions",
                "arguments": {"warehouse_id": 2, "priority": "Critical"},
            }))
        assert resp["jsonrpc"] == "2.0"
        content = resp["result"]["content"][0]["text"]
        assert "Whole Milk 1L" in content
        assert "Critical" in content

    def test_jsonrpc_call_generate_replenishment_transfers(self):
        with patch.object(inventory_mcp, "_replenishment_svc", MagicMock()) as mock_svc:
            mock_svc.generate_transfers.return_value = MOCK_GENERATE_TRANSFERS_RESULT
            resp = self.server.handle_request(_req("tools/call", {
                "name": "generate_replenishment_transfers",
                "arguments": {
                    "destination_warehouse_id": 2,
                    "items": [{"product_id": 101, "destination_warehouse_id": 2, "source_warehouse_id": 1, "suggested_transfer_qty": 70.0}],
                },
            }))
        assert resp["jsonrpc"] == "2.0"
        content = resp["result"]["content"][0]["text"]
        assert "TRF-20260826-0001" in content
        assert "transfers_created" in content

    def test_jsonrpc_read_resource_warehouse_transfers(self):
        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.list_with_lines.return_value = [MOCK_TRANSFER]
            resp = self.server.handle_request(_req("resources/read", {
                "uri": "nova://warehouse/stock-transfers",
            }))
        assert resp["jsonrpc"] == "2.0"
        assert resp["result"]["contents"][0]["uri"] == "nova://warehouse/stock-transfers"
        assert "TRF-20260826-0001" in resp["result"]["contents"][0]["text"]

    def test_jsonrpc_read_resource_replenishment_suggestions(self):
        with patch.object(inventory_mcp, "_replenishment_svc", MagicMock()) as mock_svc:
            mock_svc.get_replenishment_suggestions.return_value = MOCK_REPLENISHMENT_SUGGESTIONS
            resp = self.server.handle_request(_req("resources/read", {
                "uri": "nova://inventory/replenishment-suggestions",
            }))
        assert resp["jsonrpc"] == "2.0"
        assert resp["result"]["contents"][0]["uri"] == "nova://inventory/replenishment-suggestions"
        assert "Whole Milk 1L" in resp["result"]["contents"][0]["text"]

    def test_jsonrpc_error_handling_dispatch_missing_id(self):
        resp = self.server.handle_request(_req("tools/call", {
            "name": "dispatch_stock_transfer",
            "arguments": {"carrier": "ColdExpress"},
        }))
        assert "error" in resp
        assert resp["error"]["code"] == -32602
        assert "Transfer ID" in resp["error"]["message"]

    def test_jsonrpc_error_handling_service_runtime_error(self):
        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.create_transfer.side_effect = RuntimeError("Database connection failed")
            resp = self.server.handle_request(_req("tools/call", {
                "name": "create_stock_transfer",
                "arguments": {
                    "source_warehouse_id": 1,
                    "destination_warehouse_id": 2,
                    "lines": [{"product_id": 101, "qty_requested": 10.0}],
                },
            }))
        assert "error" in resp
        assert resp["error"]["code"] == -32603
        assert "Database connection failed" in resp["error"]["message"]


class TestMultiTenantIsolationMcp:
    """Test multi-tenant context propagation in stock transfer and replenishment MCP tool execution."""

    def setup_method(self):
        _tools.clear()
        _resources.clear()
        _prompts.clear()
        warehouse_mcp.register_tools()
        inventory_mcp.register_tools()

    def test_call_tool_propagates_tenant_context(self):
        observed_tenant = None

        def mock_list_with_lines(*args, **kwargs):
            nonlocal observed_tenant
            observed_tenant = get_current_tenant()
            return [MOCK_TRANSFER]

        with patch.object(warehouse_mcp, "_transfer_svc", MagicMock()) as mock_svc:
            mock_svc.list_with_lines.side_effect = mock_list_with_lines
            user = {"id": 12, "username": "tenant_admin", "business_id": 77}
            result = call_tool("list_stock_transfers", {}, user=user)
            assert result == [MOCK_TRANSFER]
            assert observed_tenant == 77
            # Ensure context was reset after call
            assert get_current_tenant() is None

    def test_read_resource_propagates_tenant_context(self):
        observed_tenant = None

        def mock_suggestions(*args, **kwargs):
            nonlocal observed_tenant
            observed_tenant = get_current_tenant()
            return MOCK_REPLENISHMENT_SUGGESTIONS

        with patch.object(inventory_mcp, "_replenishment_svc", MagicMock()) as mock_svc:
            mock_svc.get_replenishment_suggestions.side_effect = mock_suggestions
            user = {"id": 14, "username": "regional_mgr", "business_id": 88}
            result = read_resource("nova://inventory/replenishment-suggestions", user=user)
            assert result == MOCK_REPLENISHMENT_SUGGESTIONS
            assert observed_tenant == 88
            assert get_current_tenant() is None
