import pytest
import logging
from unittest.mock import patch, MagicMock

from packages.mcp.types import Tool, Resource, UserContext
from packages.mcp.registry import (
    register_tool, register_resource,
    call_tool, propose_action, confirm_action,
    read_resource, _tools, _resources, _pending_actions,
)
from packages.mcp.server import McpServer
from packages.redis.client import get_redis_client


class TestMcpRbacUnitAndIntegration:
    def setup_method(self):
        _tools.clear()
        _resources.clear()
        _pending_actions.clear()
        try:
            get_redis_client().flushdb()
        except Exception:
            pass

    def test_unauthorized_caller_no_user_context_rejected(self):
        """Anonymous callers without user context cannot call permission-guarded tools."""
        tool = Tool(
            name="admin_tool",
            description="Admin only tool",
            input_schema={},
            required_permission="ADMIN_VIEW",
        )
        register_tool(tool, lambda: {"status": "ok"})

        with pytest.raises(PermissionError, match="Permission denied: ADMIN_VIEW required for tool 'admin_tool'"):
            call_tool("admin_tool", {}, user=None)

    def test_unauthorized_caller_empty_permissions_rejected(self):
        """Callers with empty permissions and no role cannot access guarded tools."""
        tool = Tool(
            name="view_inventory",
            description="View inventory tool",
            input_schema={},
            required_permission="INVENTORY_VIEW",
        )
        register_tool(tool, lambda: {"items": []})

        user = {"id": 1, "username": "guest", "permissions": []}
        with pytest.raises(PermissionError, match="Permission denied: INVENTORY_VIEW required for tool 'view_inventory'"):
            call_tool("view_inventory", {}, user=user)

    def test_admin_wildcard_permission_allowed_for_all_tools(self):
        """Users with Admin role or wildcard permission '*' can access any tool."""
        admin_tool = Tool(
            name="system_reboot",
            description="Reboot system",
            input_schema={},
            required_permission="ADMIN_VIEW",
        )
        finance_tool = Tool(
            name="post_ledger",
            description="Post to GL",
            input_schema={},
            required_permission="FINANCE_VIEW",
        )
        register_tool(admin_tool, lambda: "rebooted")
        register_tool(finance_tool, lambda: "posted")

        # Admin role
        admin_user = {"id": 1, "username": "admin", "role": "Admin"}
        assert call_tool("system_reboot", {}, user=admin_user) == "rebooted"
        assert call_tool("post_ledger", {}, user=admin_user) == "posted"

        # Superadmin role
        superadmin_user = {"id": 2, "username": "super", "role": "Super Admin"}
        assert call_tool("system_reboot", {}, user=superadmin_user) == "rebooted"
        assert call_tool("post_ledger", {}, user=superadmin_user) == "posted"

        # Explicit wildcard in permissions
        wildcard_user = {"id": 3, "username": "custom_admin", "permissions": ["*"]}
        assert call_tool("system_reboot", {}, user=wildcard_user) == "rebooted"
        assert call_tool("post_ledger", {}, user=wildcard_user) == "posted"

    def test_manager_role_permissions(self):
        """Manager role can access operational domains (products, orders, invoices) but not admin tools."""
        products_tool = Tool(name="list_products", description="List products", input_schema={}, required_permission="PRODUCTS_VIEW")
        sales_tool = Tool(name="list_orders", description="List orders", input_schema={}, required_permission="SALES_VIEW")
        finance_tool = Tool(name="list_invoices", description="List invoices", input_schema={}, required_permission="FINANCE_VIEW")
        admin_tool = Tool(name="list_users", description="List users", input_schema={}, required_permission="ADMIN_VIEW")
        migration_tool = Tool(name="run_migration", description="Run migration", input_schema={}, required_permission="ADMIN_MIGRATION")

        register_tool(products_tool, lambda: ["product1", "product2"])
        register_tool(sales_tool, lambda: ["order1"])
        register_tool(finance_tool, lambda: ["inv1"])
        register_tool(admin_tool, lambda: ["user1"])
        register_tool(migration_tool, lambda: "done")

        manager = {"id": 10, "username": "mgr", "role": "Manager"}

        # Permitted tools
        assert call_tool("list_products", {}, user=manager) == ["product1", "product2"]
        assert call_tool("list_orders", {}, user=manager) == ["order1"]
        assert call_tool("list_invoices", {}, user=manager) == ["inv1"]

        # Restricted tools
        with pytest.raises(PermissionError, match="ADMIN_VIEW required"):
            call_tool("list_users", {}, user=manager)
        with pytest.raises(PermissionError, match="ADMIN_MIGRATION required"):
            call_tool("run_migration", {}, user=manager)

    def test_sales_rep_role_permissions(self):
        """Sales Rep can access sales and product tools, but not purchasing, HR, or admin tools."""
        sales_tool = Tool(name="create_order", description="Create order", input_schema={}, required_permission="SALES_VIEW")
        catalog_tool = Tool(name="get_field_sales_catalog", description="Mobile catalog", input_schema={}, required_permission="FIELD_SALES_MOBILE")
        purchasing_tool = Tool(name="list_purchase_orders", description="List POs", input_schema={}, required_permission="PURCHASING_VIEW")
        hr_tool = Tool(name="list_employees", description="List employees", input_schema={}, required_permission="HR_VIEW")
        admin_tool = Tool(name="get_audit_log", description="Audit log", input_schema={}, required_permission="ADMIN_VIEW")

        register_tool(sales_tool, lambda: {"order_id": 101})
        register_tool(catalog_tool, lambda: [{"sku": "A1"}])
        register_tool(purchasing_tool, lambda: ["po1"])
        register_tool(hr_tool, lambda: ["emp1"])
        register_tool(admin_tool, lambda: ["log1"])

        sales_rep = {"id": 20, "username": "rep1", "role": "Sales Rep"}

        # Allowed
        assert call_tool("create_order", {}, user=sales_rep) == {"order_id": 101}
        assert call_tool("get_field_sales_catalog", {}, user=sales_rep) == [{"sku": "A1"}]

        # Denied
        with pytest.raises(PermissionError, match="PURCHASING_VIEW required"):
            call_tool("list_purchase_orders", {}, user=sales_rep)
        with pytest.raises(PermissionError, match="HR_VIEW required"):
            call_tool("list_employees", {}, user=sales_rep)
        with pytest.raises(PermissionError, match="ADMIN_VIEW required"):
            call_tool("get_audit_log", {}, user=sales_rep)

    def test_cashier_role_permissions(self):
        """Cashier role can access POS and basic product views, but not purchasing or management."""
        pos_tool = Tool(name="pos_checkout", description="POS checkout", input_schema={}, required_permission="POS_VIEW")
        product_tool = Tool(name="list_products", description="List products", input_schema={}, required_permission="PRODUCTS_VIEW")
        po_tool = Tool(name="list_purchase_orders", description="List POs", input_schema={}, required_permission="PURCHASING_VIEW")
        bi_tool = Tool(name="list_kpis", description="List KPIs", input_schema={}, required_permission="BI_VIEW")

        register_tool(pos_tool, lambda: {"status": "paid"})
        register_tool(product_tool, lambda: ["item1"])
        register_tool(po_tool, lambda: [])
        register_tool(bi_tool, lambda: [])

        cashier = {"id": 30, "username": "cashier1", "role": "Cashier"}

        assert call_tool("pos_checkout", {}, user=cashier) == {"status": "paid"}
        assert call_tool("list_products", {}, user=cashier) == ["item1"]

        with pytest.raises(PermissionError, match="PURCHASING_VIEW required"):
            call_tool("list_purchase_orders", {}, user=cashier)
        with pytest.raises(PermissionError, match="BI_VIEW required"):
            call_tool("list_kpis", {}, user=cashier)

    def test_viewer_role_permissions(self):
        """Viewer role has read-only access to products/CRM, but cannot create orders or modify data."""
        view_products = Tool(name="list_products", description="List products", input_schema={}, required_permission="PRODUCTS_VIEW")
        create_order = Tool(name="create_order", description="Create order", input_schema={}, required_permission="SALES_VIEW")
        purchasing_tool = Tool(name="list_purchase_orders", description="List POs", input_schema={}, required_permission="PURCHASING_VIEW")

        register_tool(view_products, lambda: ["product1"])
        register_tool(create_order, lambda: {"id": 1})
        register_tool(purchasing_tool, lambda: [])

        viewer = {"id": 40, "username": "viewer1", "role": "Viewer"}

        assert call_tool("list_products", {}, user=viewer) == ["product1"]

        with pytest.raises(PermissionError, match="SALES_VIEW required"):
            call_tool("create_order", {}, user=viewer)
        with pytest.raises(PermissionError, match="PURCHASING_VIEW required"):
            call_tool("list_purchase_orders", {}, user=viewer)

    def test_customer_role_restricted_from_erp_tools(self):
        """Customer role with portal permissions cannot execute internal ERP tools."""
        product_tool = Tool(name="list_products", description="List products", input_schema={}, required_permission="PRODUCTS_VIEW")
        order_tool = Tool(name="list_orders", description="List orders", input_schema={}, required_permission="SALES_VIEW")
        portal_tool = Tool(name="portal_view", description="Portal view", input_schema={}, required_permission="PORTAL_VIEW")

        register_tool(product_tool, lambda: [])
        register_tool(order_tool, lambda: [])
        register_tool(portal_tool, lambda: {"portal": "ok"})

        customer = {"id": 50, "username": "client1", "role": "Customer"}

        assert call_tool("portal_view", {}, user=customer) == {"portal": "ok"}
        with pytest.raises(PermissionError, match="PRODUCTS_VIEW required"):
            call_tool("list_products", {}, user=customer)
        with pytest.raises(PermissionError, match="SALES_VIEW required"):
            call_tool("list_orders", {}, user=customer)

    def test_user_context_object_support(self):
        """Pydantic UserContext object is supported in permission extraction."""
        tool = Tool(name="sales_report", description="Sales report", input_schema={}, required_permission="SALES_VIEW")
        register_tool(tool, lambda: {"sales": 100})

        user_ctx = UserContext(id=1, username="alice", role="Sales Rep", permissions=["SALES_VIEW"])
        result = call_tool("sales_report", {}, user=user_ctx)
        assert result == {"sales": 100}

        unauthorized_ctx = UserContext(id=2, username="bob", role="Viewer", permissions=["PRODUCTS_VIEW"])
        with pytest.raises(PermissionError, match="SALES_VIEW required"):
            call_tool("sales_report", {}, user=unauthorized_ctx)

    def test_database_server_tools_require_admin(self):
        """Database server tools (list_tables, describe_table, execute_read_query) require ADMIN_VIEW."""
        from packages.mcp.servers import database_mcp
        database_mcp.register_tools()

        admin_user = {"id": 1, "username": "admin", "role": "Admin"}
        non_admin_user = {"id": 2, "username": "sales", "role": "Sales Rep"}

        with patch("packages.mcp.servers.database_mcp._list_tables", return_value=[{"table_name": "t0001"}]):
            assert call_tool("list_tables", {}, user=admin_user) == [{"table_name": "t0001"}]
            with pytest.raises(PermissionError, match="ADMIN_VIEW required for tool 'list_tables'"):
                call_tool("list_tables", {}, user=non_admin_user)

        with patch("packages.mcp.servers.database_mcp._describe_table", return_value=[{"column_name": "id"}]):
            assert call_tool("describe_table", {"table_name": "t0001"}, user=admin_user) == [{"column_name": "id"}]
            with pytest.raises(PermissionError, match="ADMIN_VIEW required for tool 'describe_table'"):
                call_tool("describe_table", {"table_name": "t0001"}, user=non_admin_user)

        with patch("packages.mcp.servers.database_mcp._execute_read_query", return_value=[{"count": 5}]):
            assert call_tool("execute_read_query", {"query": "SELECT COUNT(*) FROM t0001"}, user=admin_user) == [{"count": 5}]
            with pytest.raises(PermissionError, match="ADMIN_VIEW required for tool 'execute_read_query'"):
                call_tool("execute_read_query", {"query": "SELECT COUNT(*) FROM t0001"}, user=non_admin_user)

    def test_central_permission_mapping_fallback(self):
        """If tool object lacks required_permission attribute, fallback to MCP_TOOL_PERMISSIONS mapping."""
        tool = Tool(
            name="list_employees",  # Defined in MCP_TOOL_PERMISSIONS as HR_VIEW
            description="List employees",
            input_schema={},
            required_permission=None,
        )
        register_tool(tool, lambda: ["employee_1"])

        hr_user = {"id": 1, "role": "Manager"}  # Manager has HR_VIEW
        sales_user = {"id": 2, "role": "Sales Rep"}  # Sales Rep lacks HR_VIEW

        assert call_tool("list_employees", {}, user=hr_user) == ["employee_1"]
        with pytest.raises(PermissionError, match="HR_VIEW required"):
            call_tool("list_employees", {}, user=sales_user)

    def test_tier_2_propose_action_rbac_check(self):
        """propose_action validates permissions before returning proposal action_id."""
        tool = Tool(
            name="delete_product",
            description="Delete product",
            input_schema={"type": "object", "properties": {"id": {"type": "integer"}}},
            tier="tier2",
            required_permission="PRODUCTS_VIEW",
        )
        register_tool(tool, lambda id: f"deleted {id}")

        authorized_user = {"id": 1, "role": "Manager"}  # has PRODUCTS_VIEW
        unauthorized_user = {"id": 2, "role": "Customer"}  # lacks PRODUCTS_VIEW

        proposal = propose_action("delete_product", {"id": 10}, user=authorized_user)
        assert proposal["tool"] == "delete_product"
        assert "action_id" in proposal

        with pytest.raises(PermissionError, match="PRODUCTS_VIEW required for tool 'delete_product'"):
            propose_action("delete_product", {"id": 10}, user=unauthorized_user)

    def test_tier_2_confirm_action_rbac_check(self):
        """confirm_action enforces caller permissions upon execution."""
        tool = Tool(
            name="confirm_order",
            description="Confirm order",
            input_schema={"type": "object", "properties": {"order_id": {"type": "integer"}}},
            tier="tier2",
            required_permission="SALES_VIEW",
        )
        register_tool(tool, lambda order_id: f"confirmed {order_id}")

        sales_user = {"id": 1, "role": "Sales Rep"}
        viewer_user = {"id": 2, "role": "Viewer"}

        proposal = propose_action("confirm_order", {"order_id": 42}, user=sales_user)
        action_id = proposal["action_id"]

        # Unauthorized confirmation attempt
        with pytest.raises(PermissionError, match="SALES_VIEW required"):
            confirm_action(action_id, user=viewer_user)

    def test_protected_resource_rbac_check(self):
        """read_resource enforces required permissions on protected resources."""
        secret_res = Resource(
            uri="nova://schema",
            name="Schema",
            description="System schema",
            required_permission="ADMIN_VIEW",
        )
        register_resource(secret_res, lambda: {"tables": ["t0001", "t0021"]})

        admin_user = {"id": 1, "role": "Admin"}
        sales_user = {"id": 2, "role": "Sales Rep"}

        assert read_resource("nova://schema", user=admin_user) == {"tables": ["t0001", "t0021"]}

        with pytest.raises(PermissionError, match="ADMIN_VIEW required for resource 'nova://schema'"):
            read_resource("nova://schema", user=sales_user)

    def test_json_rpc_mcp_server_rbac_denial_error_code(self):
        """JSON-RPC server returns -32003 error code when tool execution is denied by RBAC."""
        server = McpServer(name="SecureServer", version="1.0")
        tool = Tool(
            name="admin_secret_tool",
            description="Admin only",
            input_schema={},
            required_permission="ADMIN_VIEW",
        )
        register_tool(tool, lambda: "secret_data")

        # Unauthorized request
        unauthorized_req = {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/call",
            "params": {"name": "admin_secret_tool", "arguments": {}},
        }
        resp = server.handle_request(unauthorized_req, user={"id": 5, "role": "Cashier"})
        assert resp["id"] == 101
        assert "error" in resp
        assert resp["error"]["code"] == -32003
        assert "Permission denied: ADMIN_VIEW required" in resp["error"]["message"]

        # Authorized request
        resp_admin = server.handle_request(unauthorized_req, user={"id": 1, "role": "Admin"})
        assert resp_admin["id"] == 101
        assert "result" in resp_admin
        assert "secret_data" in resp_admin["result"]["content"][0]["text"]

    def test_json_rpc_mcp_server_resource_rbac_denial(self):
        """JSON-RPC server returns -32003 error code when resource read is denied by RBAC."""
        server = McpServer(name="SecureServer", version="1.0")
        res = Resource(
            uri="nova://confidential",
            name="Confidential Doc",
            description="Confidential",
            required_permission="FINANCE_VIEW",
        )
        register_resource(res, lambda: {"financial_data": 500000})

        req = {
            "jsonrpc": "2.0",
            "id": 202,
            "method": "resources/read",
            "params": {"uri": "nova://confidential"},
        }
        resp = server.handle_request(req, user={"id": 5, "role": "Cashier"})
        assert resp["id"] == 202
        assert resp["error"]["code"] == -32003
        assert "Permission denied: FINANCE_VIEW required" in resp["error"]["message"]

    def test_security_audit_warning_logged_on_denial(self, caplog):
        """Permission denial logs a structured security warning to mcp.audit logger."""
        tool = Tool(name="restricted_tool", description="Restricted", input_schema={}, required_permission="ADMIN_VIEW")
        register_tool(tool, lambda: "ok")

        user = {"id": 99, "role": "Viewer", "business_id": 7}
        with caplog.at_level(logging.WARNING, logger="mcp.audit"):
            with pytest.raises(PermissionError):
                call_tool("restricted_tool", {}, user=user)

        assert any("status=denied" in record.message and "required_permission=ADMIN_VIEW" in record.message for record in caplog.records)
