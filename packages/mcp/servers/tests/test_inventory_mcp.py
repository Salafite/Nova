import pytest
from unittest.mock import patch, MagicMock
from packages.mcp.servers import inventory_mcp
from packages.mcp.servers.inventory_mcp import register_tools


MOCK_PRODUCT = {"id": 1, "name": "Test Product", "sku": "TST-001", "price": 10.0, "is_active": True}
MOCK_STOCK = [{"id": 1, "product_id": 1, "warehouse_id": 1, "qty": 100, "reserved_qty": 10, "reorder_level": 20}]


@pytest.fixture
def clear_registry():
    from packages.mcp import registry
    registry._tools.clear()
    registry._resources.clear()
    yield


@pytest.fixture
def mock_svc():
    with patch.multiple(inventory_mcp,
                        _products_svc=MagicMock(),
                        _categories_svc=MagicMock(),
                        _warehouses_svc=MagicMock(),
                        _uoms_svc=MagicMock(),
                        _brands_svc=MagicMock(),
                        _stock_svc=MagicMock(),
                        _replenishment_svc=MagicMock()):
        yield


class TestListProducts:
    def test_no_filters(self, mock_svc):
        inventory_mcp._products_svc.list.return_value = [MOCK_PRODUCT]
        result = inventory_mcp._list_products()
        assert result == [MOCK_PRODUCT]
        inventory_mcp._products_svc.list.assert_called_with(filters=None, limit=50, offset=0)

    def test_with_category_filter(self, mock_svc):
        inventory_mcp._products_svc.list.return_value = [MOCK_PRODUCT]
        inventory_mcp._list_products(category="Beverages")
        inventory_mcp._products_svc.list.assert_called_with(filters={"category": "Beverages"}, limit=50, offset=0)

    def test_with_catch_weight_filter(self, mock_svc):
        inventory_mcp._products_svc.list.return_value = [MOCK_PRODUCT]
        inventory_mcp._list_products(is_catch_weight=True)
        inventory_mcp._products_svc.list.assert_called_with(filters={"is_catch_weight": True}, limit=50, offset=0)


class TestGetProduct:
    def test_found(self, mock_svc):
        inventory_mcp._products_svc.get.return_value = MOCK_PRODUCT
        assert inventory_mcp._get_product(1) == MOCK_PRODUCT

    def test_not_found(self, mock_svc):
        inventory_mcp._products_svc.get.return_value = None
        assert inventory_mcp._get_product(999) is None


class TestCreateProduct:
    def test_creates_with_defaults(self, mock_svc):
        inventory_mcp._products_svc.create.return_value = MOCK_PRODUCT
        result = inventory_mcp._create_product(name="Test", sku="TST-001", price=10.0)
        inventory_mcp._products_svc.create.assert_called_with({
            "name": "Test", "sku": "TST-001", "barcode": None, "description": None,
            "type": "stockable", "price": 10.0, "cost_price": 0,
            "category": None, "brand": None, "tax_rate": 0.05,
            "weight": 0, "volume": 0, "image_url": None,
            "is_purchasable": True, "is_saleable": True, "is_active": True,
            "is_catch_weight": False, "pricing_uom_id": None,
            "nominal_weight": None, "tolerance_pct": None, "pricing_basis": "weight",
        })
        assert result == MOCK_PRODUCT

    def test_creates_catch_weight_product(self, mock_svc):
        cw_product = {
            **MOCK_PRODUCT,
            "is_catch_weight": True,
            "pricing_uom_id": 2,
            "nominal_weight": 10.0,
            "tolerance_pct": 5.0,
            "pricing_basis": "weight",
        }
        inventory_mcp._products_svc.create.return_value = cw_product
        result = inventory_mcp._create_product(
            name="Cheddar Cheese Block",
            sku="CW-CHD-001",
            price=45.0,
            is_catch_weight=True,
            pricing_uom_id=2,
            nominal_weight=10.0,
            tolerance_pct=5.0,
            pricing_basis="weight",
        )
        inventory_mcp._products_svc.create.assert_called_with({
            "name": "Cheddar Cheese Block", "sku": "CW-CHD-001", "barcode": None, "description": None,
            "type": "stockable", "price": 45.0, "cost_price": 0,
            "category": None, "brand": None, "tax_rate": 0.05,
            "weight": 0, "volume": 0, "image_url": None,
            "is_purchasable": True, "is_saleable": True, "is_active": True,
            "is_catch_weight": True, "pricing_uom_id": 2,
            "nominal_weight": 10.0, "tolerance_pct": 5.0, "pricing_basis": "weight",
        })
        assert result == cw_product


class TestUpdateProduct:
    def test_updates_only_provided_fields(self, mock_svc):
        inventory_mcp._products_svc.update.return_value = MOCK_PRODUCT
        inventory_mcp._update_product(id=1, name="Updated", price=15.0)
        inventory_mcp._products_svc.update.assert_called_with(1, {"name": "Updated", "price": 15.0})

    def test_updates_catch_weight_fields(self, mock_svc):
        cw_updated = {
            **MOCK_PRODUCT,
            "is_catch_weight": True,
            "pricing_uom_id": 2,
            "nominal_weight": 12.5,
            "tolerance_pct": 7.5,
            "pricing_basis": "weight",
        }
        inventory_mcp._products_svc.update.return_value = cw_updated
        result = inventory_mcp._update_product(
            id=1,
            is_catch_weight=True,
            pricing_uom_id=2,
            nominal_weight=12.5,
            tolerance_pct=7.5,
            pricing_basis="weight",
        )
        inventory_mcp._products_svc.update.assert_called_with(1, {
            "is_catch_weight": True,
            "pricing_uom_id": 2,
            "nominal_weight": 12.5,
            "tolerance_pct": 7.5,
            "pricing_basis": "weight",
        })
        assert result == cw_updated


class TestDeleteProduct:
    def test_deletes(self, mock_svc):
        inventory_mcp._products_svc.delete.return_value = True
        assert inventory_mcp._delete_product(1) is True


class TestCheckStock:
    def test_returns_available_qty(self, mock_svc):
        inventory_mcp._stock_svc.list.return_value = MOCK_STOCK
        result = inventory_mcp._check_stock(product_id=1)
        assert result[0]["available_qty"] == 90

    def test_filters_by_warehouse(self, mock_svc):
        inventory_mcp._stock_svc.list.return_value = MOCK_STOCK
        inventory_mcp._check_stock(product_id=1, warehouse_id=2)
        inventory_mcp._stock_svc.list.assert_called_with(filters={"product_id": 1, "warehouse_id": 2})


class TestSearchProducts:
    def test_executes_ilike_query(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [MOCK_PRODUCT]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        with patch("packages.mcp.servers.inventory_mcp.get_connection", return_value=mock_conn):
            with patch("packages.mcp.servers.inventory_mcp.release_connection"):
                result = inventory_mcp._search_products(query="test")
                assert result == [MOCK_PRODUCT]
                args = mock_cur.execute.call_args[0][1]
                assert args == ("%test%", "%test%", 20)

    def test_executes_ilike_query_with_tenant(self):
        from modules.core.context import tenant_context
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [MOCK_PRODUCT]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        with tenant_context(42):
            with patch("packages.mcp.servers.inventory_mcp.get_connection", return_value=mock_conn):
                with patch("packages.mcp.servers.inventory_mcp.release_connection"):
                    result = inventory_mcp._search_products(query="test")
                    assert result == [MOCK_PRODUCT]
                    sql = mock_cur.execute.call_args[0][0]
                    args = mock_cur.execute.call_args[0][1]
                    assert "business_id = %s" in sql
                    assert args == (42, "%test%", "%test%", 20)

    def test_releases_connection(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        with patch("packages.mcp.servers.inventory_mcp.get_connection", return_value=mock_conn):
            with patch("packages.mcp.servers.inventory_mcp.release_connection") as release:
                inventory_mcp._search_products(query="x")
                release.assert_called_once_with(mock_conn)


class TestListHelpers:
    def test_categories(self, mock_svc):
        inventory_mcp._categories_svc.list.return_value = [{"id": 1, "name": "Drinks"}]
        assert inventory_mcp._list_categories() == [{"id": 1, "name": "Drinks"}]

    def test_warehouses(self, mock_svc):
        inventory_mcp._warehouses_svc.list.return_value = [{"id": 1, "name": "Main"}]
        assert inventory_mcp._list_warehouses() == [{"id": 1, "name": "Main"}]

    def test_uoms(self, mock_svc):
        inventory_mcp._uoms_svc.list.return_value = [{"id": 1, "uom_code": "KG"}]
        assert inventory_mcp._list_uoms() == [{"id": 1, "uom_code": "KG"}]

    def test_brands(self, mock_svc):
        inventory_mcp._brands_svc.list.return_value = [{"id": 1, "name": "NovaBrand"}]
        assert inventory_mcp._list_brands() == [{"id": 1, "name": "NovaBrand"}]


class TestReplenishmentSuggestions:
    def test_list_replenishment_suggestions_default(self, mock_svc):
        mock_resp = {
            "total_suggestions": 1,
            "critical_count": 1,
            "high_count": 0,
            "items": [{
                "product_id": 1,
                "product_name": "Test Product",
                "destination_warehouse_id": 2,
                "suggested_transfer_qty": 50.0,
                "source_warehouse_id": 1,
                "priority": "Critical",
            }],
        }
        inventory_mcp._replenishment_svc.get_replenishment_suggestions.return_value = mock_resp
        result = inventory_mcp._list_replenishment_suggestions()
        assert result == mock_resp
        inventory_mcp._replenishment_svc.get_replenishment_suggestions.assert_called_once_with(
            warehouse_id=None,
            source_warehouse_id=None,
            product_id=None,
            category=None,
            priority=None,
            min_deficit=0.0,
            safety_stock_ratio=0.5,
            target_coverage_multiplier=1.5,
        )

    def test_list_replenishment_suggestions_with_filters(self, mock_svc):
        mock_resp = {"total_suggestions": 0, "critical_count": 0, "high_count": 0, "items": []}
        inventory_mcp._replenishment_svc.get_replenishment_suggestions.return_value = mock_resp
        result = inventory_mcp._list_replenishment_suggestions(
            warehouse_id=2,
            source_warehouse_id=1,
            product_id=5,
            category="Dairy",
            priority="Critical",
            min_deficit=10.0,
            safety_stock_ratio=0.6,
            target_coverage_multiplier=2.0,
        )
        assert result == mock_resp
        inventory_mcp._replenishment_svc.get_replenishment_suggestions.assert_called_once_with(
            warehouse_id=2,
            source_warehouse_id=1,
            product_id=5,
            category="Dairy",
            priority="Critical",
            min_deficit=10.0,
            safety_stock_ratio=0.6,
            target_coverage_multiplier=2.0,
        )

    def test_list_replenishment_suggestions_alias_destination_warehouse_id(self, mock_svc):
        mock_resp = {"total_suggestions": 0, "items": []}
        inventory_mcp._replenishment_svc.get_replenishment_suggestions.return_value = mock_resp
        result = inventory_mcp._list_replenishment_suggestions(destination_warehouse_id=3)
        assert result == mock_resp
        inventory_mcp._replenishment_svc.get_replenishment_suggestions.assert_called_once_with(
            warehouse_id=3,
            source_warehouse_id=None,
            product_id=None,
            category=None,
            priority=None,
            min_deficit=0.0,
            safety_stock_ratio=0.5,
            target_coverage_multiplier=1.5,
        )


class TestGenerateReplenishmentTransfers:
    def test_generate_replenishment_transfers(self, mock_svc):
        mock_resp = {
            "transfers_created": 1,
            "transfer_ids": [101],
            "transfer_numbers": ["TRF-20260826-0001"],
            "transfers": [{"id": 101, "transfer_number": "TRF-20260826-0001", "status": "Draft"}],
        }
        inventory_mcp._replenishment_svc.generate_transfers.return_value = mock_resp
        items = [{"product_id": 1, "destination_warehouse_id": 2, "source_warehouse_id": 1, "suggested_transfer_qty": 50.0}]
        result = inventory_mcp._generate_replenishment_transfers(
            destination_warehouse_id=2,
            source_warehouse_id=1,
            items=items,
            carrier="FastLogistics",
            notes="Auto replen",
        )
        assert result == mock_resp
        inventory_mcp._replenishment_svc.generate_transfers.assert_called_once_with(
            payload={
                "destination_warehouse_id": 2,
                "source_warehouse_id": 1,
                "items": items,
                "transfer_date": None,
                "expected_delivery_date": None,
                "carrier": "FastLogistics",
                "notes": "Auto replen",
            },
            user_id=None,
        )

    def test_generate_replenishment_transfers_with_user_context(self, mock_svc):
        mock_resp = {
            "transfers_created": 1,
            "transfer_ids": [102],
            "transfer_numbers": ["TRF-20260826-0002"],
            "transfers": [{"id": 102, "transfer_number": "TRF-20260826-0002"}],
        }
        inventory_mcp._replenishment_svc.generate_transfers.return_value = mock_resp
        with patch("packages.mcp.servers.inventory_mcp.get_current_user", return_value={"id": 7, "username": "warehouse_manager"}):
            result = inventory_mcp._generate_replenishment_transfers(destination_warehouse_id=2)
            assert result == mock_resp
            inventory_mcp._replenishment_svc.generate_transfers.assert_called_once_with(
                payload={
                    "destination_warehouse_id": 2,
                    "source_warehouse_id": None,
                    "items": None,
                    "transfer_date": None,
                    "expected_delivery_date": None,
                    "carrier": None,
                    "notes": None,
                },
                user_id=7,
            )


class TestRegisterTools:
    def test_registers_all_tools_and_resources(self, clear_registry):
        register_tools()
        from packages.mcp.registry import get_tools, list_resources
        tool_names = [t.name for t in get_tools()]
        assert "list_products" in tool_names
        assert "get_product" in tool_names
        assert "create_product" in tool_names
        assert "update_product" in tool_names
        assert "delete_product" in tool_names
        assert "search_products" in tool_names
        assert "check_stock" in tool_names
        assert "list_categories" in tool_names
        assert "list_warehouses" in tool_names
        assert "list_uoms" in tool_names
        assert "list_brands" in tool_names
        assert "list_replenishment_suggestions" in tool_names
        assert "generate_replenishment_transfers" in tool_names
        resource_uris = [r.uri for r in list_resources()]
        assert "nova://inventory/products" in resource_uris
        assert "nova://inventory/replenishment-suggestions" in resource_uris
