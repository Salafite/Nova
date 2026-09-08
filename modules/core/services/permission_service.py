import re

# Centralized mapping of T-codes to required permission keys
T_CODE_PERMISSIONS: dict[str, str] = {
    # Foundation / Inventory / Products
    'T0001': 'PRODUCTS_VIEW',      # UOM
    'T0002': 'PRODUCTS_VIEW',      # UOM Conversion
    'T0003': 'PRODUCTS_VIEW',      # Products
    'T0004': 'PRODUCTS_VIEW',      # Barcodes
    'T0005': 'PRODUCTS_VIEW',      # Attr Definitions
    'T0006': 'PRODUCTS_VIEW',      # Attr Values
    'T0007': 'PRODUCTS_VIEW',      # Product UOM
    'T0008': 'WAREHOUSE_VIEW',     # Warehouses
    'T0009': 'INVENTORY_VIEW',     # Stock Levels / Inventory
    'T0010': 'CRM_VIEW',           # Customers
    'T0011': 'PURCHASING_VIEW',    # Suppliers
    'T0012': 'SALES_VIEW',         # Sales Orders
    'T0013': 'SALES_VIEW',         # Sales Lines
    'T0014': 'PURCHASING_VIEW',    # Purchase Orders
    'T0015': 'PURCHASING_VIEW',    # Purchase Lines
    'T0016': 'SALES_VIEW',         # Installment Plans
    'T0017': 'SALES_VIEW',         # Install Payments
    'T0018': 'MFG_VIEW',           # Manufacturing Orders
    'T0019': 'MFG_VIEW',           # QC Inspections
    'T0020': 'MFG_VIEW',           # Shop Floor Jobs
    'T0021': 'ADMIN_VIEW',         # System Users
    'T0022': 'ADMIN_VIEW',         # Nav Permissions
    'T0023': 'ADMIN_VIEW',         # Audit Log
    'T0024': 'PLANNING_VIEW',      # Production Plans
    'T0025': 'ADMIN_VIEW',         # Global Settings
    'T0026': 'FINANCE_VIEW',       # Chart of Accounts
    'T0027': 'FINANCE_VIEW',       # Journal Entries
    'T0028': 'HR_VIEW',            # Departments
    'T0029': 'HR_VIEW',            # Designations
    'T0030': 'HR_VIEW',            # Employees
    'T0031': 'HR_VIEW',            # Employee Contracts
    'T0032': 'HR_VIEW',            # Employee Documents
    'T0033': 'HR_VIEW',            # Shifts
    'T0034': 'HR_VIEW',            # Attendance
    'T0035': 'HR_VIEW',            # Leave Types
    'T0036': 'HR_VIEW',            # Leave Requests
    'T0037': 'HR_VIEW',            # Payroll Periods
    'T0038': 'HR_VIEW',            # Payroll Entries
    'T0039': 'HR_VIEW',            # Job Openings
    'T0040': 'HR_VIEW',            # Candidates
    'T0041': 'MAINTENANCE_VIEW',   # Assets
    'T0042': 'MAINTENANCE_VIEW',   # Maintenance Schedules
    'T0043': 'MAINTENANCE_VIEW',   # Maintenance Work Orders
    'T0044': 'PROJECTS_VIEW',      # Projects
    'T0045': 'PROJECTS_VIEW',      # Project Tasks
    'T0046': 'PROJECTS_VIEW',      # Resource Allocations
    'T0047': 'PROJECTS_VIEW',      # Timesheets
    'T0048': 'PROJECTS_VIEW',      # Service Requests
    'T0049': 'PROJECTS_VIEW',      # Contracts
    'T0050': 'PROJECTS_VIEW',      # SLA Definitions
    'T0051': 'DASHBOARD_VIEW',     # Search Index
    'T0052': 'BI_VIEW',            # KPI Definitions
    'T0053': 'BI_VIEW',            # KPI Values
    'T0054': 'BI_VIEW',            # BI Dashboards
    'T0055': 'BI_VIEW',            # Dashboard Widgets
    'T0056': 'INTEGRATIONS_VIEW',  # API Keys
    'T0057': 'INTEGRATIONS_VIEW',  # Integration Configs
    'T0058': 'INTEGRATIONS_VIEW',  # Sync Logs
    'T0059': 'ADMIN_VIEW',         # Tenants
    'T0060': 'ADMIN_VIEW',         # Workflow Definitions
    'T0061': 'ADMIN_VIEW',         # Workflow Instances
    'T0062': 'ADMIN_VIEW',         # Documents
    'T0063': 'ADMIN_VIEW',         # Compliance Rules
    'T0064': 'INVENTORY_VIEW',     # Stock Movements
    'T0065': 'MFG_VIEW',           # Bill of Materials
    'T0066': 'MFG_VIEW',           # BOM Lines
    'T0067': 'SALES_VIEW',         # Sales Quotations
    'T0068': 'SALES_VIEW',         # Sales Quotation Lines
    'T0069': 'PURCHASING_VIEW',    # Purchase Requisitions
    'T0070': 'PURCHASING_VIEW',    # Purchase Requisition Lines
    'T0071': 'PURCHASING_VIEW',    # RFQs
    'T0072': 'PURCHASING_VIEW',    # RFQ Lines
    'T0073': 'PURCHASING_VIEW',    # RFQ Vendors
    'T0074': 'PURCHASING_VIEW',    # RFQ Quotes
    'T0075': 'WAREHOUSE_VIEW',     # Goods Receipts
    'T0076': 'WAREHOUSE_VIEW',     # Goods Receipt Lines
    'T0077': 'SALES_VIEW',         # Deliveries
    'T0078': 'SALES_VIEW',         # Delivery Lines
    'T0079': 'SALES_VIEW',         # Sales Returns
    'T0080': 'SALES_VIEW',         # Sales Return Lines
    'T0081': 'PURCHASING_VIEW',    # Purchase Returns
    'T0082': 'PURCHASING_VIEW',    # Purchase Return Lines
    'T0083': 'SALES_VIEW',         # Price Lists
    'T0084': 'SALES_VIEW',         # Price List Items
    'T0085': 'SALES_VIEW',         # Tax Rates
    'T0086': 'SALES_VIEW',         # Tax Rules
    'T0087': 'INVENTORY_VIEW',     # Serial Numbers
    'T0088': 'INVENTORY_VIEW',     # Batch Numbers
    'T0089': 'FINANCE_VIEW',       # Journal Entry Lines
    'T0090': 'FINANCE_VIEW',       # Invoices
    'T0091': 'FINANCE_VIEW',       # Payments
    'T0092': 'CRM_VIEW',           # Leads
    'T0093': 'CRM_VIEW',           # Lead Activities
    'T0094': 'CRM_VIEW',           # Opportunities
    'T0095': 'CRM_VIEW',           # Opportunity Lines
    'T0096': 'FINANCE_VIEW',       # Payment Terms
    'T0097': 'FINANCE_VIEW',       # Payment Methods
    'T0098': 'ADMIN_VIEW',         # User Notifications
    'T0099': 'ADMIN_VIEW',         # Scheduled Tasks
    'T0100': 'ADMIN_VIEW',         # Module Registry
    'T0101': 'WAREHOUSE_VIEW',     # Pick Lists
    'T0103': 'PURCHASING_VIEW',    # Product Suppliers
    'T0104': 'ADMIN_MIGRATION',     # Data Migration
    'T0105': 'INVENTORY_VIEW',     # Inventory Counts
    'T0106': 'INVENTORY_VIEW',     # Inventory Count Items
    'T0107': 'PRODUCTS_VIEW',      # Product Types
    'T0108': 'WAREHOUSE_VIEW',     # Stock Transfers
    'T0109': 'WAREHOUSE_VIEW',     # Stock Transfer Lines
    'T0110': 'SALES_VIEW',         # Commission Payouts
    'T0116': 'ACCOUNTING_VIEW',    # Bank Statements
    'T0117': 'ACCOUNTING_VIEW',    # Statement Transactions
    'T0118': 'ACCOUNTING_VIEW',    # Check Clearing Records
    'T0120': 'SALES_VIEW',         # Volume Tier Breaks
    'T0121': 'SALES_VIEW',         # Customer Group Price Lists
    'T0122': 'SALES_VIEW',         # Customer Contracts
    'T0123': 'SALES_VIEW',         # Promotional Campaign Rules
    'T0124': 'WAREHOUSE_VIEW',     # Warehouse Temperature Zones
    'T0125': 'WAREHOUSE_VIEW',     # Warehouse Bins & Staging Areas
    'T0126': 'WAREHOUSE_VIEW',     # Vehicle Temperature Compartments
    'T0127': 'QUALITY_VIEW',       # Temperature Excursion Alerts
    'T0128': 'QUALITY_VIEW',       # HACCP Checkpoint Logs & Compliance Reports
}

# Non-T-code custom route and tag mappings
CUSTOM_ROUTE_PERMISSIONS: dict[str, str] = {
    '/api/categories': 'PRODUCTS_VIEW',
    '/api/v1/migration': 'ADMIN_MIGRATION',
    '/api/v1/migration/connectors/test': 'ADMIN_MIGRATION',
    '/api/v1/migration/connectors/discover': 'ADMIN_MIGRATION',
    '/api/v1/migration/connectors/preview': 'ADMIN_MIGRATION',
    '/api/v1/migration/dry-run': 'ADMIN_MIGRATION',
    '/api/v1/migration/commit': 'ADMIN_MIGRATION',
    '/api/v1/migration/rollback': 'ADMIN_MIGRATION',
    '/api/v1/migration/batches': 'ADMIN_MIGRATION',
    '/api/v1/migration/upload': 'ADMIN_MIGRATION',
    '/api/bi/dashboard': 'BI_VIEW',
    '/api/bi/executive': 'BI_VIEW',
    '/api/bi/executive/export': 'BI_VIEW',
    '/api/sales/commission': 'SALES_VIEW',
    '/api/admin/users': 'ADMIN_VIEW',
    '/api/adjustments': 'INVENTORY_VIEW',
    '/api/pos': 'POS_VIEW',
    '/api/portal': 'PORTAL_VIEW',
    '/api/portal/orders': 'PORTAL_ORDER',
    '/api/portal/invoices': 'PORTAL_PAY',
    '/api/T0025I': 'ADMIN_VIEW',
    '/api/T0100I': 'ADMIN_VIEW',
    '/api/T0104I': 'ADMIN_MIGRATION',
    '/api/sales/mobile': 'FIELD_SALES_MOBILE',
    'Categories': 'PRODUCTS_VIEW',
    'Migration': 'ADMIN_MIGRATION',
    'Data Migration': 'ADMIN_MIGRATION',
    'Legacy Migration': 'ADMIN_MIGRATION',
    'T0104 - Data Migration': 'ADMIN_MIGRATION',
    'T0104 - Legacy Migration': 'ADMIN_MIGRATION',
    'ADMIN_MIGRATION': 'ADMIN_MIGRATION',
    'BI Dashboard': 'BI_VIEW',
    'Executive Analytics': 'BI_VIEW',
    'Executive Financial Exports': 'BI_VIEW',
    'Sales Commissions': 'SALES_VIEW',
    'T0109 - Commission Rules': 'SALES_VIEW',
    'T0110 - Commission Payouts': 'SALES_VIEW',
    'T0108 - Stock Transfers': 'WAREHOUSE_VIEW',
    'T0109 - Stock Transfer Lines': 'WAREHOUSE_VIEW',
    'T0116 - Bank Statements': 'ACCOUNTING_VIEW',
    'T0117 - Statement Transactions': 'ACCOUNTING_VIEW',
    'T0118 - Check Clearing Records': 'ACCOUNTING_VIEW',
    '/api/T0108I': 'WAREHOUSE_VIEW',
    '/api/T0109I': 'WAREHOUSE_VIEW',
    '/api/T0116I': 'ACCOUNTING_VIEW',
    '/api/T0117I': 'ACCOUNTING_VIEW',
    '/api/T0118I': 'ACCOUNTING_VIEW',
    'T0120 - Customer Group Price Mappings': 'SALES_VIEW',
    'T0121 - Promotional Campaign Rules': 'SALES_VIEW',
    '/api/T0120I': 'SALES_VIEW',
    '/api/T0121I': 'SALES_VIEW',
    'Admin User Preferences': 'ADMIN_VIEW',
    'Stock Adjustments': 'INVENTORY_VIEW',
    'POS': 'POS_VIEW',
    'Customer Portal': 'PORTAL_VIEW',
    'Portal Orders': 'PORTAL_ORDER',
    'Portal Invoices': 'PORTAL_PAY',
    'T0025 - Global Settings': 'ADMIN_VIEW',
    'T0100 - Module Registry': 'ADMIN_VIEW',
    '/api/inventory/replenishment': 'INVENTORY_VIEW',
    '/api/purchasing/restock': 'PURCHASING_VIEW',
    'Inventory - Inter-Branch Replenishment': 'INVENTORY_VIEW',
    'Purchasing - Proactive Demand Restock': 'PURCHASING_VIEW',
    'Replenishment': 'INVENTORY_VIEW',
    'Field Sales Mobile': 'FIELD_SALES_MOBILE',
    'Field Sales': 'FIELD_SALES_MOBILE',
}

# Role to granted permissions mapping
_ROLE_PERMISSIONS: dict[str, list[str]] = {
    'Admin': ['*'],
    'Administrator': ['*'],
    'Superadmin': ['*'],
    'Super Admin': ['*'],
    'Manager': [
        'DASHBOARD_VIEW',
        'SALES_VIEW',
        'POS_VIEW',
        'CRM_VIEW',
        'CUSTOMERS_VIEW',
        'SUPPLIERS_VIEW',
        'PURCHASING_VIEW',
        'PRODUCTS_VIEW',
        'INVENTORY_VIEW',
        'WAREHOUSE_VIEW',
        'FINANCE_VIEW',
        'ACCOUNTING_VIEW',
        'MFG_VIEW',
        'PLANNING_VIEW',
        'SHOPFLOOR_VIEW',
        'QUALITY_VIEW',
        'PROJECTS_VIEW',
        'MAINTENANCE_VIEW',
        'BI_VIEW',
        'HR_VIEW',
        'FIELD_SALES_MOBILE',
    ],
    'Sales Manager': [
        'DASHBOARD_VIEW',
        'SALES_VIEW',
        'POS_VIEW',
        'CRM_VIEW',
        'CUSTOMERS_VIEW',
        'SUPPLIERS_VIEW',
        'PURCHASING_VIEW',
        'PRODUCTS_VIEW',
        'INVENTORY_VIEW',
        'WAREHOUSE_VIEW',
        'FINANCE_VIEW',
        'ACCOUNTING_VIEW',
        'BI_VIEW',
        'FIELD_SALES_MOBILE',
    ],
    'Sales Rep': [
        'DASHBOARD_VIEW',
        'SALES_VIEW',
        'POS_VIEW',
        'CRM_VIEW',
        'CUSTOMERS_VIEW',
        'PRODUCTS_VIEW',
        'INVENTORY_VIEW',
        'FIELD_SALES_MOBILE',
    ],
    'Cashier': [
        'DASHBOARD_VIEW',
        'POS_VIEW',
        'SALES_VIEW',
        'CRM_VIEW',
        'CUSTOMERS_VIEW',
        'PRODUCTS_VIEW',
    ],
    'Viewer': [
        'DASHBOARD_VIEW',
        'PRODUCTS_VIEW',
        'CRM_VIEW',
        'CUSTOMERS_VIEW',
    ],
    'Customer': [
        'PORTAL_VIEW',
        'PORTAL_ORDER',
        'PORTAL_PAY',
    ],
    'Financial Manager': [
        'DASHBOARD_VIEW',
        'FINANCE_VIEW',
        'ACCOUNTING_VIEW',
        'SALES_VIEW',
        'CRM_VIEW',
        'CUSTOMERS_VIEW',
        'PURCHASING_VIEW',
        'SUPPLIERS_VIEW',
        'PRODUCTS_VIEW',
        'INVENTORY_VIEW',
        'BI_VIEW',
    ],
    'Warehouse Manager': [
        'DASHBOARD_VIEW',
        'WAREHOUSE_VIEW',
        'INVENTORY_VIEW',
        'PRODUCTS_VIEW',
        'PURCHASING_VIEW',
    ],
    'Purchasing Manager': [
        'DASHBOARD_VIEW',
        'PURCHASING_VIEW',
        'SUPPLIERS_VIEW',
        'PRODUCTS_VIEW',
        'INVENTORY_VIEW',
        'WAREHOUSE_VIEW',
        'FINANCE_VIEW',
    ],
    'HR Manager': [
        'DASHBOARD_VIEW',
        'HR_VIEW',
    ],
    'Project Manager': [
        'DASHBOARD_VIEW',
        'PROJECTS_VIEW',
    ],
    'Manufacturing Manager': [
        'DASHBOARD_VIEW',
        'MFG_VIEW',
        'PLANNING_VIEW',
        'SHOPFLOOR_VIEW',
        'QUALITY_VIEW',
        'INVENTORY_VIEW',
        'WAREHOUSE_VIEW',
    ],
}

# Centralized mapping of MCP tool names to required permission keys
MCP_TOOL_PERMISSIONS: dict[str, str] = {
    # Database Server
    'list_tables': 'ADMIN_VIEW',
    'describe_table': 'ADMIN_VIEW',
    'execute_read_query': 'ADMIN_VIEW',

    # Admin Server
    'list_users': 'ADMIN_VIEW',
    'get_audit_log': 'ADMIN_VIEW',
    'list_settings': 'ADMIN_VIEW',
    'get_setting': 'ADMIN_VIEW',
    'list_notifications': 'ADMIN_VIEW',
    'list_scheduled_tasks': 'ADMIN_VIEW',
    'list_modules': 'ADMIN_VIEW',

    # Notifications Server
    'list_user_notifications': 'ADMIN_VIEW',
    'mark_notification_read': 'ADMIN_VIEW',
    'mark_all_notifications_read': 'ADMIN_VIEW',

    # Migration Server
    'test_legacy_connection': 'ADMIN_MIGRATION',
    'discover_legacy_schema': 'ADMIN_MIGRATION',
    'run_migration_dry_run': 'ADMIN_MIGRATION',
    'commit_migration_batch': 'ADMIN_MIGRATION',
    'rollback_migration_batch': 'ADMIN_MIGRATION',
    'get_migration_reconciliation': 'ADMIN_MIGRATION',

    # Inventory Server
    'list_products': 'PRODUCTS_VIEW',
    'get_product': 'PRODUCTS_VIEW',
    'create_product': 'PRODUCTS_VIEW',
    'update_product': 'PRODUCTS_VIEW',
    'delete_product': 'PRODUCTS_VIEW',
    'search_products': 'PRODUCTS_VIEW',
    'check_stock': 'INVENTORY_VIEW',
    'list_categories': 'PRODUCTS_VIEW',
    'list_warehouses': 'WAREHOUSE_VIEW',
    'list_uoms': 'PRODUCTS_VIEW',
    'list_brands': 'PRODUCTS_VIEW',
    'list_replenishment_suggestions': 'INVENTORY_VIEW',
    'generate_replenishment_transfers': 'INVENTORY_VIEW',

    # Warehouse Server
    'list_goods_receipts': 'WAREHOUSE_VIEW',
    'list_serial_numbers': 'INVENTORY_VIEW',
    'list_batch_numbers': 'INVENTORY_VIEW',
    'get_batch_number': 'INVENTORY_VIEW',
    'allocate_fefo_lots': 'WAREHOUSE_VIEW',
    'list_pick_lists': 'WAREHOUSE_VIEW',
    'get_pick_list': 'WAREHOUSE_VIEW',
    'pick_item': 'WAREHOUSE_VIEW',
    'approve_pick_tolerance': 'WAREHOUSE_VIEW',
    'check_pick_list_discrepancies': 'WAREHOUSE_VIEW',
    'get_batch_recall_report': 'WAREHOUSE_VIEW',
    'list_stock_transfers': 'WAREHOUSE_VIEW',
    'get_stock_transfer': 'WAREHOUSE_VIEW',
    'create_stock_transfer': 'WAREHOUSE_VIEW',
    'dispatch_stock_transfer': 'WAREHOUSE_VIEW',
    'receive_stock_transfer': 'WAREHOUSE_VIEW',
    'verify_barcode': 'WAREHOUSE_VIEW',
    'verify_pick_barcode': 'WAREHOUSE_VIEW',
    'verify_goods_receipt_barcode': 'WAREHOUSE_VIEW',

    # Sales Server
    'list_orders': 'SALES_VIEW',
    'get_order': 'SALES_VIEW',
    'create_order': 'SALES_VIEW',
    'create_order_line': 'SALES_VIEW',
    'list_order_lines': 'SALES_VIEW',
    'update_order_status': 'SALES_VIEW',
    'confirm_order': 'SALES_VIEW',
    'cancel_order': 'SALES_VIEW',
    'list_customers': 'CRM_VIEW',
    'get_customer_aging': 'SALES_VIEW',
    'list_quotations': 'SALES_VIEW',
    'convert_quotation_to_order': 'SALES_VIEW',
    'list_deliveries': 'SALES_VIEW',
    'list_price_lists': 'SALES_VIEW',
    'list_tax_rates': 'SALES_VIEW',
    'get_field_sales_catalog': 'FIELD_SALES_MOBILE',
    'sync_offline_orders': 'FIELD_SALES_MOBILE',
    'check_offline_order_conflicts': 'FIELD_SALES_MOBILE',
    'calculate_sales_rep_commissions': 'SALES_VIEW',
    'recalculate_order_catch_weight': 'SALES_VIEW',
    'check_customer_credit': 'SALES_VIEW',
    'override_credit_hold': 'SALES_VIEW',
    'reject_credit_hold': 'SALES_VIEW',
    'capture_proof_of_delivery': 'SALES_VIEW',
    'log_cod_collection': 'SALES_VIEW',
    'get_delivery_fulfillment_metrics': 'SALES_VIEW',
    'get_driver_handover_report': 'SALES_VIEW',

    # POS Server
    'pos_customer_lookup': 'POS_VIEW',
    'pos_checkout': 'POS_VIEW',

    # Purchasing Server
    'list_purchase_orders': 'PURCHASING_VIEW',
    'get_purchase_order': 'PURCHASING_VIEW',
    'list_purchase_returns': 'PURCHASING_VIEW',
    'list_rfqs': 'PURCHASING_VIEW',
    'calculate_restock_forecast': 'PURCHASING_VIEW',
    'propose_draft_purchase_order': 'PURCHASING_VIEW',

    # Accounting Server
    'list_chart_of_accounts': 'FINANCE_VIEW',
    'list_invoices': 'FINANCE_VIEW',
    'get_invoice': 'FINANCE_VIEW',
    'list_payments': 'FINANCE_VIEW',
    'list_payment_terms': 'FINANCE_VIEW',
    'get_payment_term': 'FINANCE_VIEW',
    'preview_invoice_early_discount': 'FINANCE_VIEW',
    'parse_bank_statement': 'ACCOUNTING_VIEW',
    'auto_match_bank_statement_checks': 'ACCOUNTING_VIEW',
    'confirm_batch_check_clearing': 'ACCOUNTING_VIEW',
    'list_bounced_checks': 'ACCOUNTING_VIEW',
    'process_bounced_check': 'ACCOUNTING_VIEW',

    # HR Server
    'list_employees': 'HR_VIEW',
    'get_employee': 'HR_VIEW',
    'list_departments': 'HR_VIEW',
    'list_attendance': 'HR_VIEW',
    'list_leave_requests': 'HR_VIEW',
    'list_payroll_entries': 'HR_VIEW',
    'list_shifts': 'HR_VIEW',
    'list_job_openings': 'HR_VIEW',

    # BI Server
    'list_kpis': 'BI_VIEW',
    'get_kpi_values': 'BI_VIEW',
    'list_dashboards': 'BI_VIEW',
    'get_dashboard_widgets': 'BI_VIEW',
    'get_customer_profitability_matrix': 'BI_VIEW',
    'get_product_category_margins': 'BI_VIEW',
    'get_executive_margin_summary': 'BI_VIEW',
    'export_executive_analytics_report': 'BI_VIEW',

    # CRM Server
    'list_leads': 'CRM_VIEW',
    'list_opportunities': 'CRM_VIEW',
    'list_suppliers': 'PURCHASING_VIEW',
    'list_customer_groups': 'CRM_VIEW',

    # Projects Server
    'list_projects': 'PROJECTS_VIEW',
    'get_project': 'PROJECTS_VIEW',
    'list_tasks': 'PROJECTS_VIEW',
    'list_milestones': 'PROJECTS_VIEW',

    # Manufacturing Server
    'list_manufacturing_orders': 'MFG_VIEW',
    'list_boms': 'MFG_VIEW',
    'list_qc_inspections': 'MFG_VIEW',
    'list_shop_jobs': 'MFG_VIEW',

    # Maintenance Server
    'list_assets': 'MAINTENANCE_VIEW',
    'list_maintenance_schedules': 'MAINTENANCE_VIEW',
    'list_work_orders': 'MAINTENANCE_VIEW',
}


def derive_permissions(role: str) -> list[str]:
    """Return default permissions list for a given user role."""
    if not role:
        return ['DASHBOARD_VIEW']
    if role in _ROLE_PERMISSIONS:
        return _ROLE_PERMISSIONS[role]
    normalized = str(role).strip().lower()
    normalized_spaced = normalized.replace('_', ' ')
    for k, v in _ROLE_PERMISSIONS.items():
        k_lower = k.lower()
        if k_lower == normalized or k_lower == normalized_spaced:
            return v
    if "manager" in normalized or "admin" in normalized:
        return _ROLE_PERMISSIONS.get("Manager", ['DASHBOARD_VIEW'])
    return ['DASHBOARD_VIEW']


def get_required_permission(prefix: str = '', tag: str = '') -> str:
    """Resolve the required permission key for an endpoint prefix or controller tag."""
    # 1. Exact custom route / tag match
    if prefix in CUSTOM_ROUTE_PERMISSIONS:
        return CUSTOM_ROUTE_PERMISSIONS[prefix]
    if tag in CUSTOM_ROUTE_PERMISSIONS:
        return CUSTOM_ROUTE_PERMISSIONS[tag]

    # Prefix hierarchy check for migration routes
    if prefix.startswith('/api/v1/migration'):
        return 'ADMIN_MIGRATION'

    # 2. Extract T-code from prefix (e.g. /api/T0001I -> T0001) or tag (e.g. T0001 - UOM)
    match = re.search(r'T(\d{4})', prefix) or re.search(r'T(\d{4})', tag)
    if match:
        tcode = f"T{match.group(1)}"
        if tcode in T_CODE_PERMISSIONS:
            return T_CODE_PERMISSIONS[tcode]

    # 3. Default fallback
    return 'ADMIN_VIEW'


def get_mcp_tool_permission(tool_name: str) -> str | None:
    """Return the required permission key for an MCP tool name, or None if not restricted."""
    return MCP_TOOL_PERMISSIONS.get(tool_name)


def has_permission(user_permissions: list[str] | None, required_permission: str | None) -> bool:
    """Check if the provided user permissions satisfy the required permission."""
    if not required_permission:
        return True
    if not user_permissions:
        return False
    if '*' in user_permissions:
        return True
    if required_permission in user_permissions:
        return True
    if required_permission == 'ADMIN_MIGRATION' and 'ADMIN_VIEW' in user_permissions:
        return True
    if required_permission in ('FINANCE_VIEW', 'ACCOUNTING_VIEW') and ('FINANCE_VIEW' in user_permissions or 'ACCOUNTING_VIEW' in user_permissions):
        return True
    return False
