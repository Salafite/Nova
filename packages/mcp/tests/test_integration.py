from unittest.mock import patch, MagicMock
from packages.mcp.server import McpServer
from packages.mcp.registry import _tools, _resources, _prompts

from packages.mcp.servers.database_mcp import register_tools as reg_db
from packages.mcp.servers.inventory_mcp import register_tools as reg_inventory
from packages.mcp.servers.sales_mcp import register_tools as reg_sales
from packages.mcp.servers.purchasing_mcp import register_tools as reg_purchasing
from packages.mcp.servers.accounting_mcp import register_tools as reg_accounting
from packages.mcp.servers.admin_mcp import register_tools as reg_admin
from packages.mcp.servers.warehouse_mcp import register_tools as reg_warehouse
from packages.mcp.servers.hr_mcp import register_tools as reg_hr
from packages.mcp.servers.bi_mcp import register_tools as reg_bi
from packages.mcp.servers.crm_mcp import register_tools as reg_crm
from packages.mcp.servers.projects_mcp import register_tools as reg_projects
from packages.mcp.servers.manufacturing_mcp import register_tools as reg_manufacturing
from packages.mcp.servers.maintenance_mcp import register_tools as reg_maintenance
from packages.mcp.servers.notifications_mcp import register_tools as reg_notifications


ALL_TOOL_NAMES = [
    "list_tables", "describe_table", "execute_read_query",
    "list_products", "get_product", "create_product", "update_product", "delete_product",
    "search_products", "check_stock", "list_categories", "list_warehouses", "list_uoms", "list_brands",
    "list_orders", "get_order", "create_order", "update_order_status",
    "confirm_order", "cancel_order",
    "list_customers", "get_customer_aging", "list_quotations", "convert_quotation_to_order",
    "list_deliveries", "list_price_lists", "list_tax_rates",
    "list_purchase_orders", "get_purchase_order", "list_purchase_returns", "list_rfqs",
    "list_chart_of_accounts", "list_invoices", "get_invoice", "list_payments", "list_payment_terms",
    "list_users", "get_audit_log", "list_settings", "get_setting",
    "list_notifications", "list_scheduled_tasks", "list_modules",
    "list_goods_receipts", "list_serial_numbers", "list_batch_numbers", "list_pick_lists",
    "list_employees", "get_employee", "list_departments", "list_attendance",
    "list_leave_requests", "list_payroll_entries", "list_shifts", "list_job_openings",
    "list_kpis", "get_kpi_values", "list_dashboards", "get_dashboard_widgets",
    "list_leads", "list_opportunities", "list_suppliers", "list_customer_groups",
    "list_projects", "get_project", "list_tasks", "list_milestones",
    "list_manufacturing_orders", "list_boms", "list_qc_inspections", "list_shop_jobs",
    "list_assets", "list_maintenance_schedules", "list_work_orders",
    "list_user_notifications", "mark_notification_read", "mark_all_notifications_read",
]

DB_MODULES = {
    "packages.mcp.servers.inventory_mcp": "inventory_mcp",
    "packages.mcp.servers.sales_mcp": "sales_mcp",
    "packages.mcp.servers.purchasing_mcp": "purchasing_mcp",
    "packages.mcp.servers.accounting_mcp": "accounting_mcp",
    "packages.mcp.servers.admin_mcp": "admin_mcp",
    "packages.mcp.servers.warehouse_mcp": "warehouse_mcp",
    "packages.mcp.servers.hr_mcp": "hr_mcp",
    "packages.mcp.servers.bi_mcp": "bi_mcp",
    "packages.mcp.servers.crm_mcp": "crm_mcp",
    "packages.mcp.servers.projects_mcp": "projects_mcp",
    "packages.mcp.servers.manufacturing_mcp": "manufacturing_mcp",
    "packages.mcp.servers.maintenance_mcp": "maintenance_mcp",
    "packages.mcp.servers.notifications_mcp": "notifications_mcp",
}


def _req(method, params=None, req_id=1):
    msg = {"jsonrpc": "2.0", "method": method, "id": req_id}
    if params:
        msg["params"] = params
    return msg


class TestMcpIntegration:
    def setup_method(self):
        _tools.clear()
        _resources.clear()
        _prompts.clear()
        self.server = McpServer(name="IntegrationTest", version="1.0")

    def _register_all(self):
        reg_db()
        reg_inventory()
        reg_sales()
        reg_purchasing()
        reg_accounting()
        reg_admin()
        reg_warehouse()
        reg_hr()
        reg_bi()
        reg_crm()
        reg_projects()
        reg_manufacturing()
        reg_maintenance()
        reg_notifications()

    def test_tools_list_returns_all_tools(self):
        self._register_all()
        resp = self.server.handle_request(_req("tools/list"))
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        tools = resp["result"]["tools"]
        names = [t["name"] for t in tools]
        assert len(names) == len(set(names))
        for name in ALL_TOOL_NAMES:
            assert name in names, f"Missing tool: {name}"

    def test_initialize(self):
        self._register_all()
        resp = self.server.handle_request(_req("initialize", {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "test", "version": "1.0"},
        }))
        assert resp["jsonrpc"] == "2.0"
        assert resp["result"]["serverInfo"]["name"] == "IntegrationTest"
        assert resp["result"]["protocolVersion"] == "2024-11-05"

    def test_ping(self):
        self._register_all()
        resp = self.server.handle_request(_req("ping"))
        assert resp["result"] == {}

    def test_method_not_found(self):
        self._register_all()
        resp = self.server.handle_request(_req("unknown_method"))
        assert resp["error"]["code"] == -32601

    def test_tool_not_found(self):
        self._register_all()
        resp = self.server.handle_request(_req("tools/call", {
            "name": "nonexistent", "arguments": {},
        }))
        assert resp["error"]["code"] == -32602
        assert "Tool not found" in resp["error"]["message"]

    def test_tool_call_missing_arguments(self):
        self._register_all()
        import packages.mcp.servers.admin_mcp as m
        with patch.object(m, "_users_svc", MagicMock()) as svc:
            svc.list.return_value = [{"username": "admin"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_users", "arguments": {},
            }))
        assert resp["result"]["content"][0]["type"] == "text"

    def test_database_list_tables(self):
        self._register_all()
        with (
            patch("packages.mcp.servers.database_mcp.get_connection") as mock_get,
            patch("packages.mcp.servers.database_mcp.release_connection"),
        ):
            mock_conn = MagicMock()
            mock_get.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {"table_name": "t0001", "table_type": "TABLE"},
            ]
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_tables", "arguments": {},
            }))
        assert resp["jsonrpc"] == "2.0"
        assert "t0001" in resp["result"]["content"][0]["text"]

    def test_database_describe_table(self):
        self._register_all()
        with (
            patch("packages.mcp.servers.database_mcp.get_connection") as mock_get,
            patch("packages.mcp.servers.database_mcp.release_connection"),
        ):
            mock_conn = MagicMock()
            mock_get.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {"column_name": "id", "data_type": "integer", "is_nullable": "NO"},
            ]
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            resp = self.server.handle_request(_req("tools/call", {
                "name": "describe_table", "arguments": {"table_name": "t0001"},
            }))
        assert resp["jsonrpc"] == "2.0"
        assert "id" in resp["result"]["content"][0]["text"]

    def test_database_execute_read_query_rejects_write(self):
        self._register_all()
        resp = self.server.handle_request(_req("tools/call", {
            "name": "execute_read_query", "arguments": {"sql": "DROP TABLE users"},
        }))
        assert resp["error"]["code"] == -32602

    def test_inventory_list_products(self):
        self._register_all()
        import packages.mcp.servers.inventory_mcp as m
        with patch.object(m, "_products_svc", MagicMock()) as svc:
            svc.list.return_value = [{"id": 1, "name": "Widget", "price": 10.0}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_products", "arguments": {},
            }))
        assert resp["jsonrpc"] == "2.0"
        assert "Widget" in resp["result"]["content"][0]["text"]

    def test_inventory_get_product(self):
        self._register_all()
        import packages.mcp.servers.inventory_mcp as m
        with patch.object(m, "_products_svc", MagicMock()) as svc:
            svc.get.return_value = {"id": 42, "name": "Gadget"}
            resp = self.server.handle_request(_req("tools/call", {
                "name": "get_product", "arguments": {"id": 42},
            }))
        assert resp["jsonrpc"] == "2.0"
        assert "Gadget" in resp["result"]["content"][0]["text"]

    def test_inventory_create_product(self):
        self._register_all()
        import packages.mcp.servers.inventory_mcp as m
        with patch.object(m, "_products_svc", MagicMock()) as svc:
            svc.create.return_value = {"id": 10, "name": "NewItem"}
            resp = self.server.handle_request(_req("tools/call", {
                "name": "create_product", "arguments": {"name": "NewItem", "sku": "N001"},
            }))
        assert resp["jsonrpc"] == "2.0"
        assert "NewItem" in resp["result"]["content"][0]["text"]

    def test_inventory_delete_product(self):
        self._register_all()
        import packages.mcp.servers.inventory_mcp as m
        with patch.object(m, "_products_svc", MagicMock()) as svc:
            svc.delete.return_value = {"deleted": True}
            resp = self.server.handle_request(_req("tools/call", {
                "name": "delete_product", "arguments": {"id": 1},
            }))
        assert resp["jsonrpc"] == "2.0"

    def test_inventory_check_stock(self):
        self._register_all()
        import packages.mcp.servers.inventory_mcp as m
        with patch.object(m, "_stock_svc", MagicMock()) as svc:
            svc.list.return_value = [{"product_id": 1, "warehouse_id": 1, "available_qty": 50}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "check_stock", "arguments": {"product_id": 1},
            }))
        assert resp["jsonrpc"] == "2.0"

    def test_sales_list_orders(self):
        self._register_all()
        import packages.mcp.servers.sales_mcp as m
        with patch.object(m, "_orders_svc", MagicMock()) as svc:
            svc.list.return_value = [{"id": 1, "order_number": "SO-001"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_orders", "arguments": {},
            }))
        assert "SO-001" in resp["result"]["content"][0]["text"]

    def test_sales_get_order(self):
        self._register_all()
        import packages.mcp.servers.sales_mcp as m
        with patch.object(m, "_orders_svc", MagicMock()) as svc:
            svc.get.return_value = {"id": 5, "order_number": "SO-005"}
            resp = self.server.handle_request(_req("tools/call", {
                "name": "get_order", "arguments": {"id": 5},
            }))
        assert "SO-005" in resp["result"]["content"][0]["text"]

    def test_sales_create_order(self):
        self._register_all()
        import packages.mcp.servers.sales_mcp as m
        with patch.object(m, "_orders_svc", MagicMock()) as svc:
            svc.create.return_value = {"id": 1, "grand_total": 110.0}
            resp = self.server.handle_request(_req("tools/call", {
                "name": "create_order", "arguments": {"customer_id": 1},
            }))
        assert resp["jsonrpc"] == "2.0"

    def test_sales_confirm_order(self):
        self._register_all()
        import packages.mcp.servers.sales_mcp as m
        with patch.object(m, "_orders_svc", MagicMock()) as svc:
            resp = self.server.handle_request(_req("tools/call", {
                "name": "confirm_order", "arguments": {"id": 1},
            }))
        assert resp["jsonrpc"] == "2.0"

    def test_sales_cancel_order(self):
        self._register_all()
        import packages.mcp.servers.sales_mcp as m
        with patch.object(m, "_orders_svc", MagicMock()) as svc:
            resp = self.server.handle_request(_req("tools/call", {
                "name": "cancel_order", "arguments": {"id": 1},
            }))
        assert resp["jsonrpc"] == "2.0"

    def test_sales_list_customers(self):
        self._register_all()
        import packages.mcp.servers.sales_mcp as m
        with patch.object(m, "_customers_svc", MagicMock()) as svc:
            svc.list.return_value = [{"id": 1, "customer_name": "Acme"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_customers", "arguments": {},
            }))
        assert "Acme" in resp["result"]["content"][0]["text"]

    def test_sales_list_quotations(self):
        self._register_all()
        import packages.mcp.servers.sales_mcp as m
        with patch.object(m, "_quotations_svc", MagicMock()) as svc:
            svc.list.return_value = [{"id": 1, "quotation_number": "Q-001"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_quotations", "arguments": {},
            }))
        assert "Q-001" in resp["result"]["content"][0]["text"]

    def test_sales_convert_quotation(self):
        self._register_all()
        import packages.mcp.servers.sales_mcp as m
        with patch.object(m, "_quotations_svc", MagicMock()) as svc:
            svc.update.return_value = {"id": 1, "status": "Converted"}
            resp = self.server.handle_request(_req("tools/call", {
                "name": "convert_quotation_to_order", "arguments": {"id": 1},
            }))
        assert resp["jsonrpc"] == "2.0"
        assert "Converted" in resp["result"]["content"][0]["text"]

    def test_purchasing_list_po(self):
        self._register_all()
        import packages.mcp.servers.purchasing_mcp as m
        with patch.object(m, "_po_svc", MagicMock()) as svc:
            svc.list.return_value = [{"id": 1, "order_number": "PO-001"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_purchase_orders", "arguments": {},
            }))
        assert "PO-001" in resp["result"]["content"][0]["text"]

    def test_purchasing_get_po(self):
        self._register_all()
        import packages.mcp.servers.purchasing_mcp as m
        with patch.object(m, "_po_svc", MagicMock()) as svc:
            svc.get.return_value = {"id": 5, "order_number": "PO-005"}
            resp = self.server.handle_request(_req("tools/call", {
                "name": "get_purchase_order", "arguments": {"id": 5},
            }))
        assert "PO-005" in resp["result"]["content"][0]["text"]

    def test_accounting_list_coa(self):
        self._register_all()
        import packages.mcp.servers.accounting_mcp as m
        with patch.object(m, "_coa_svc", MagicMock()) as svc:
            svc.list.return_value = [{"id": 1, "account_code": "1000"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_chart_of_accounts", "arguments": {},
            }))
        assert "1000" in resp["result"]["content"][0]["text"]

    def test_accounting_list_invoices(self):
        self._register_all()
        import packages.mcp.servers.accounting_mcp as m
        with patch.object(m, "_inv_svc", MagicMock()) as svc:
            svc.list.return_value = [{"id": 1, "invoice_number": "INV-001"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_invoices", "arguments": {},
            }))
        assert "INV-001" in resp["result"]["content"][0]["text"]

    def test_accounting_get_invoice(self):
        self._register_all()
        import packages.mcp.servers.accounting_mcp as m
        with patch.object(m, "_inv_svc", MagicMock()) as svc:
            svc.get.return_value = {"id": 3, "total_amount": 500}
            resp = self.server.handle_request(_req("tools/call", {
                "name": "get_invoice", "arguments": {"id": 3},
            }))
        assert "500" in resp["result"]["content"][0]["text"]

    def test_admin_list_users(self):
        self._register_all()
        import packages.mcp.servers.admin_mcp as m
        with patch.object(m, "_users_svc", MagicMock()) as svc:
            svc.list.return_value = [{"username": "admin"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_users", "arguments": {},
            }))
        assert "admin" in resp["result"]["content"][0]["text"]

    def test_admin_get_setting(self):
        self._register_all()
        import packages.mcp.servers.admin_mcp as m
        with patch.object(m, "_settings_svc", MagicMock()) as svc:
            svc.list.return_value = [{"setting_key": "x", "setting_value": "y"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "get_setting", "arguments": {"key": "x"},
            }))
        assert "y" in resp["result"]["content"][0]["text"]

    def test_admin_get_setting_not_found(self):
        self._register_all()
        import packages.mcp.servers.admin_mcp as m
        with patch.object(m, "_settings_svc", MagicMock()) as svc:
            svc.list.return_value = []
            resp = self.server.handle_request(_req("tools/call", {
                "name": "get_setting", "arguments": {"key": "nonexistent"},
            }))
        assert resp["result"]["content"][0]["text"].strip() == "null"

    def test_warehouse_list_gr(self):
        self._register_all()
        import packages.mcp.servers.warehouse_mcp as m
        with patch.object(m, "_gr_svc", MagicMock()) as svc:
            svc.list.return_value = [{"goods_receipt_number": "GR-001"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_goods_receipts", "arguments": {},
            }))
        assert "GR-001" in resp["result"]["content"][0]["text"]

    def test_hr_list_employees(self):
        self._register_all()
        import packages.mcp.servers.hr_mcp as m
        with patch.object(m, "_emp_svc", MagicMock()) as svc:
            svc.list.return_value = [{"full_name": "John"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_employees", "arguments": {},
            }))
        assert "John" in resp["result"]["content"][0]["text"]

    def test_hr_get_employee(self):
        self._register_all()
        import packages.mcp.servers.hr_mcp as m
        with patch.object(m, "_emp_svc", MagicMock()) as svc:
            svc.get.return_value = {"id": 1, "full_name": "Jane"}
            resp = self.server.handle_request(_req("tools/call", {
                "name": "get_employee", "arguments": {"id": 1},
            }))
        assert "Jane" in resp["result"]["content"][0]["text"]

    def test_bi_list_kpis(self):
        self._register_all()
        import packages.mcp.servers.bi_mcp as m
        with patch.object(m, "_kpi_def_svc", MagicMock()) as svc:
            svc.list.return_value = [{"kpi_name": "Revenue"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_kpis", "arguments": {},
            }))
        assert "Revenue" in resp["result"]["content"][0]["text"]

    def test_crm_list_leads(self):
        self._register_all()
        import packages.mcp.servers.crm_mcp as m
        with patch.object(m, "_leads_svc", MagicMock()) as svc:
            svc.list.return_value = [{"first_name": "John", "last_name": "Doe"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_leads", "arguments": {},
            }))
        assert "John" in resp["result"]["content"][0]["text"]

    def test_projects_list_projects(self):
        self._register_all()
        import packages.mcp.servers.projects_mcp as m
        with patch.object(m, "_proj_svc", MagicMock()) as svc:
            svc.list.return_value = [{"project_name": "Nova ERP"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_projects", "arguments": {},
            }))
        assert "Nova ERP" in resp["result"]["content"][0]["text"]

    def test_manufacturing_list_mfg(self):
        self._register_all()
        import packages.mcp.servers.manufacturing_mcp as m
        with patch.object(m, "_mfg_svc", MagicMock()) as svc:
            svc.list.return_value = [{"order_number": "MFG-001"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_manufacturing_orders", "arguments": {},
            }))
        assert "MFG-001" in resp["result"]["content"][0]["text"]

    def test_maintenance_list_assets(self):
        self._register_all()
        import packages.mcp.servers.maintenance_mcp as m
        with patch.object(m, "_asset_svc", MagicMock()) as svc:
            svc.list.return_value = [{"asset_name": "Forklift"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_assets", "arguments": {},
            }))
        assert "Forklift" in resp["result"]["content"][0]["text"]

    def test_notifications_list(self):
        self._register_all()
        import packages.mcp.servers.notifications_mcp as m
        with patch.object(m, "_notif_svc", MagicMock()) as svc:
            svc.list.return_value = [{"title": "Alert"}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "list_user_notifications", "arguments": {"user_id": 1},
            }))
        assert "Alert" in resp["result"]["content"][0]["text"]

    def test_notifications_mark_read(self):
        self._register_all()
        import packages.mcp.servers.notifications_mcp as m
        with patch.object(m, "_notif_svc", MagicMock()) as svc:
            resp = self.server.handle_request(_req("tools/call", {
                "name": "mark_notification_read", "arguments": {"id": 5},
            }))
        assert resp["jsonrpc"] == "2.0"
        svc.update.assert_called_with(5, {"is_read": True})

    def test_notifications_mark_all_read(self):
        self._register_all()
        import packages.mcp.servers.notifications_mcp as m
        with patch.object(m, "_notif_svc", MagicMock()) as svc:
            svc.list.return_value = [{"id": 1}, {"id": 2}]
            resp = self.server.handle_request(_req("tools/call", {
                "name": "mark_all_notifications_read", "arguments": {"user_id": 1},
            }))
        assert resp["jsonrpc"] == "2.0"
        assert '"updated": 2' in resp["result"]["content"][0]["text"]

    def test_handler_exception_returns_error(self):
        _tools.clear()
        from packages.mcp.types import Tool
        from packages.mcp.registry import register_tool
        register_tool(Tool(name="broken", description="Always fails", input_schema={}),
                      lambda: (_ for _ in ()).throw(RuntimeError("oops")))
        resp = self.server.handle_request(_req("tools/call", {
            "name": "broken", "arguments": {},
        }))
        assert resp["error"]["code"] == -32603

    def test_resources_available(self):
        self._register_all()
        resp = self.server.handle_request(_req("resources/list"))
        assert resp["jsonrpc"] == "2.0"
        uris = [r["uri"] for r in resp["result"]["resources"]]
        assert "nova://schema" in uris
        assert "nova://inventory/products" in uris
        assert "nova://sales/orders" in uris
