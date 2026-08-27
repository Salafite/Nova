from unittest.mock import patch, MagicMock
from packages.mcp.servers import warehouse_mcp
from packages.mcp.servers.warehouse_mcp import register_tools


class TestWarehouseMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()

    def _test(self, fn_name, svc_name, expected):
        mod = warehouse_mcp
        with patch.object(mod, svc_name, MagicMock()) as mock:
            mock.list.return_value = [expected]
            fn = getattr(mod, fn_name)
            result = fn()
            assert result == [expected]

    def test_list_gr(self):
        self._test("_list_gr", "_gr_svc", {"id": 1, "receipt_number": "GR-001"})

    def test_list_serial(self):
        self._test("_list_serial", "_serial_svc", {"id": 1, "serial_number": "SN-001"})

    def test_list_batch(self):
        self._test("_list_batch", "_batch_svc", {"id": 1, "batch_number": "BT-001"})

    def test_list_pick(self):
        self._test("_list_pick", "_pick_svc", {"id": 1, "pick_list_number": "PL-001"})

    def test_get_pick_list(self):
        mod = warehouse_mcp
        mock_detail = {
            "id": 1,
            "pick_list_number": "PL-001",
            "items": [{
                "id": 10,
                "product_name": "Cheddar",
                "qty_ordered": 2,
                "qty_picked": 2,
                "catch_weight_actual": 9.8,
                "nominal_weight": 10.0,
                "tolerance_status": "Within Tolerance",
            }],
        }
        with patch.object(mod, "_pick_svc", MagicMock()) as mock:
            mock.get_with_items.return_value = mock_detail
            result = mod._get_pick_list(1)
            assert result == mock_detail
            mock.get_with_items.assert_called_once_with(1)

    def test_pick_item(self):
        mod = warehouse_mcp
        mock_item = {
            "id": 10,
            "qty_picked": 2,
            "catch_weight_actual": 10.5,
            "catch_weight_uom": "kg",
            "nominal_weight": 10.0,
            "tolerance_pct": 5.0,
            "tolerance_variance_pct": 5.0,
            "tolerance_status": "Within Tolerance",
        }
        with patch.object(mod, "_pick_svc", MagicMock()) as mock:
            mock.pick_item.return_value = mock_item
            result = mod._pick_item(
                item_id=10,
                qty_picked=2,
                pick_list_id=1,
                catch_weight_actual=10.5,
                catch_weight_uom="kg",
                nominal_weight=10.0,
                tolerance_pct=5.0,
            )
            assert result == mock_item
            mock.pick_item.assert_called_once_with(
                item_id=10,
                qty_picked=2,
                pick_list_id=1,
                catch_weight_actual=10.5,
                catch_weight_uom="kg",
                nominal_weight=10.0,
                tolerance_pct=5.0,
                picked_batch_id=None,
                picked_batch_number=None,
            )

    def test_approve_pick_tolerance(self):
        mod = warehouse_mcp
        mock_result = {
            "id": 1,
            "items": [{
                "id": 10,
                "tolerance_status": "Approved",
                "supervisor_approved": True,
            }],
        }
        with patch.object(mod, "_pick_svc", MagicMock()) as mock:
            mock.approve_tolerance.return_value = mock_result
            result = mod._approve_pick_tolerance(
                pick_list_id=1,
                item_id=10,
                supervisor_id=5,
                supervisor_notes="Approved variance by supervisor",
            )
            assert result == mock_result
            mock.approve_tolerance.assert_called_once_with(
                pick_list_id=1,
                item_id=10,
                item_ids=None,
                supervisor_id=5,
                supervisor_notes="Approved variance by supervisor",
            )

    def test_approve_pick_tolerance_multiple_items(self):
        mod = warehouse_mcp
        mock_result = {
            "id": 1,
            "items": [
                {"id": 10, "tolerance_status": "Approved", "supervisor_approved": True},
                {"id": 11, "tolerance_status": "Approved", "supervisor_approved": True},
            ],
        }
        with patch.object(mod, "_pick_svc", MagicMock()) as mock:
            mock.approve_tolerance.return_value = mock_result
            result = mod._approve_pick_tolerance(
                pick_list_id=1,
                item_ids=[10, 11],
                supervisor_id=5,
                supervisor_notes="Approved batch variance",
            )
            assert result == mock_result
            mock.approve_tolerance.assert_called_once_with(
                pick_list_id=1,
                item_id=None,
                item_ids=[10, 11],
                supervisor_id=5,
                supervisor_notes="Approved batch variance",
            )

    def test_check_pick_list_discrepancies(self):
        mod = warehouse_mcp
        mock_discrepancies = [{
            "id": 10,
            "product_name": "Gouda Cheese",
            "tolerance_status": "Out of Tolerance",
            "supervisor_approved": False,
        }]
        with patch.object(mod, "_pick_svc", MagicMock()) as mock:
            mock.check_pick_list_discrepancies.return_value = mock_discrepancies
            result = mod._check_pick_list_discrepancies(1)
            assert result == mock_discrepancies
            mock.check_pick_list_discrepancies.assert_called_once_with(1)

    def test_get_batch_recall_report(self):
        mod = warehouse_mcp
        with patch.object(mod, "_batch_svc", MagicMock()) as mock:
            mock.get_recall_report.return_value = {
                "batch": {"batch_number": "LOT-RECALL-99"},
                "affected_customers": [{"customer_name": "Acme Supermarket"}]
            }
            result = mod._get_batch_recall_report(batch_number="LOT-RECALL-99")
            assert result["batch"]["batch_number"] == "LOT-RECALL-99"
            assert len(result["affected_customers"]) == 1
            mock.get_recall_report.assert_called_once_with(
                batch_number="LOT-RECALL-99",
                batch_id=None,
                product_id=None
            )

    def test_get_batch_recall_report_missing_args(self):
        result = warehouse_mcp._get_batch_recall_report()
        assert "error" in result

    def test_list_stock_transfers(self):
        mod = warehouse_mcp
        mock_transfer = {"id": 1, "transfer_number": "TRF-20260826-0001", "status": "In Transit"}
        with patch.object(mod, "_transfer_svc", MagicMock()) as mock:
            mock.list_with_lines.return_value = [mock_transfer]
            result = mod._list_stock_transfers(status="In Transit", source_warehouse_id=1, destination_warehouse_id=2)
            assert result == [mock_transfer]
            mock.list_with_lines.assert_called_once_with(
                filters={"status": "In Transit", "source_warehouse_id": 1, "destination_warehouse_id": 2},
                limit=50,
                offset=0,
            )

    def test_get_stock_transfer(self):
        mod = warehouse_mcp
        mock_detail = {
            "id": 1,
            "transfer_number": "TRF-20260826-0001",
            "status": "In Transit",
            "lines": [{"id": 10, "product_id": 5, "qty_requested": 100}],
        }
        with patch.object(mod, "_transfer_svc", MagicMock()) as mock:
            mock.get_transfer_with_lines.return_value = mock_detail
            result = mod._get_stock_transfer(1)
            assert result == mock_detail
            mock.get_transfer_with_lines.assert_called_once_with(1)

    def test_create_stock_transfer(self):
        mod = warehouse_mcp
        mock_created = {"id": 1, "transfer_number": "TRF-20260826-0001", "status": "Draft"}
        with patch.object(mod, "_transfer_svc", MagicMock()) as mock:
            mock.create_transfer.return_value = mock_created
            lines = [{"product_id": 101, "qty_requested": 50.0}]
            result = mod._create_stock_transfer(
                source_warehouse_id=1,
                destination_warehouse_id=2,
                lines=lines,
                carrier="FastLogistics",
                tracking_number="TRACK-123",
                notes="Priority transfer",
            )
            assert result == mock_created
            mock.create_transfer.assert_called_once_with({
                "source_warehouse_id": 1,
                "destination_warehouse_id": 2,
                "lines": lines,
                "carrier": "FastLogistics",
                "tracking_number": "TRACK-123",
                "notes": "Priority transfer",
            })

    def test_dispatch_stock_transfer(self):
        mod = warehouse_mcp
        mock_dispatched = {"id": 1, "status": "In Transit", "carrier": "Express Freight"}
        with patch.object(mod, "_transfer_svc", MagicMock()) as mock:
            mock.dispatch_transfer.return_value = mock_dispatched
            lines = [{"line_id": 10, "qty_dispatched": 50.0}]
            result = mod._dispatch_stock_transfer(
                id=1,
                carrier="Express Freight",
                tracking_number="EXP-999",
                dispatched_by=3,
                lines=lines,
            )
            assert result == mock_dispatched
            mock.dispatch_transfer.assert_called_once_with(
                1,
                dispatch_data={
                    "carrier": "Express Freight",
                    "tracking_number": "EXP-999",
                    "dispatched_by": 3,
                    "lines": lines,
                },
            )

    def test_receive_stock_transfer(self):
        mod = warehouse_mcp
        mock_received = {"id": 1, "status": "Received"}
        with patch.object(mod, "_transfer_svc", MagicMock()) as mock:
            mock.receive_transfer.return_value = mock_received
            lines = [{"line_id": 10, "qty_received": 48.0, "qty_lost": 2.0, "loss_reason": "Damage"}]
            result = mod._receive_stock_transfer(
                id=1,
                received_by=4,
                lines=lines,
                notes="2 units damaged during transport",
            )
            assert result == mock_received
            mock.receive_transfer.assert_called_once_with(
                1,
                receive_data={
                    "received_by": 4,
                    "notes": "2 units damaged during transport",
                    "lines": lines,
                },
            )

    def test_register_tools(self):
        register_tools()
        from packages.mcp.registry import get_tools, list_resources
        names = [t.name for t in get_tools()]
        assert "list_goods_receipts" in names
        assert "list_serial_numbers" in names
        assert "list_batch_numbers" in names
        assert "list_pick_lists" in names
        assert "get_pick_list" in names
        assert "pick_item" in names
        assert "approve_pick_tolerance" in names
        assert "check_pick_list_discrepancies" in names
        assert "get_batch_recall_report" in names
        assert "list_stock_transfers" in names
        assert "get_stock_transfer" in names
        assert "create_stock_transfer" in names
        assert "dispatch_stock_transfer" in names
        assert "receive_stock_transfer" in names
        uris = [r.uri for r in list_resources()]
        assert "nova://warehouse/pick-lists" in uris
        assert "nova://warehouse/stock-transfers" in uris

