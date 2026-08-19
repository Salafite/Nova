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
    'T0104': 'ADMIN_VIEW',         # Data Migration
    'T0105': 'INVENTORY_VIEW',     # Inventory Counts
    'T0106': 'INVENTORY_VIEW',     # Inventory Count Items
    'T0107': 'PRODUCTS_VIEW',      # Product Types
}

# Non-T-code custom route and tag mappings
CUSTOM_ROUTE_PERMISSIONS: dict[str, str] = {
    '/api/categories': 'PRODUCTS_VIEW',
    '/api/v1/migration': 'ADMIN_VIEW',
    '/api/bi/dashboard': 'BI_VIEW',
    '/api/admin/users': 'ADMIN_VIEW',
    '/api/adjustments': 'INVENTORY_VIEW',
    '/api/pos': 'POS_VIEW',
    '/api/T0025I': 'ADMIN_VIEW',
    '/api/T0100I': 'ADMIN_VIEW',
    'Categories': 'PRODUCTS_VIEW',
    'Migration': 'ADMIN_VIEW',
    'BI Dashboard': 'BI_VIEW',
    'Admin User Preferences': 'ADMIN_VIEW',
    'Stock Adjustments': 'INVENTORY_VIEW',
    'POS': 'POS_VIEW',
    'T0025 - Global Settings': 'ADMIN_VIEW',
    'T0100 - Module Registry': 'ADMIN_VIEW',
}

# Role to granted permissions mapping
_ROLE_PERMISSIONS: dict[str, list[str]] = {
    'Admin': ['*'],
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
        'MFG_VIEW',
        'PLANNING_VIEW',
        'SHOPFLOOR_VIEW',
        'QUALITY_VIEW',
        'PROJECTS_VIEW',
        'MAINTENANCE_VIEW',
        'BI_VIEW',
        'HR_VIEW',
    ],
    'Sales Rep': [
        'DASHBOARD_VIEW',
        'SALES_VIEW',
        'POS_VIEW',
        'CRM_VIEW',
        'CUSTOMERS_VIEW',
        'PRODUCTS_VIEW',
        'INVENTORY_VIEW',
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
}


def derive_permissions(role: str) -> list[str]:
    """Return default permissions list for a given user role."""
    return _ROLE_PERMISSIONS.get(role, ['DASHBOARD_VIEW'])


def get_required_permission(prefix: str = '', tag: str = '') -> str:
    """Resolve the required permission key for an endpoint prefix or controller tag."""
    # 1. Exact custom route / tag match
    if prefix in CUSTOM_ROUTE_PERMISSIONS:
        return CUSTOM_ROUTE_PERMISSIONS[prefix]
    if tag in CUSTOM_ROUTE_PERMISSIONS:
        return CUSTOM_ROUTE_PERMISSIONS[tag]

    # 2. Extract T-code from prefix (e.g. /api/T0001I -> T0001) or tag (e.g. T0001 - UOM)
    match = re.search(r'T(\d{4})', prefix) or re.search(r'T(\d{4})', tag)
    if match:
        tcode = f"T{match.group(1)}"
        if tcode in T_CODE_PERMISSIONS:
            return T_CODE_PERMISSIONS[tcode]

    # 3. Default fallback
    return 'ADMIN_VIEW'


def has_permission(user_permissions: list[str] | None, required_permission: str | None) -> bool:
    """Check if the provided user permissions satisfy the required permission."""
    if not required_permission:
        return True
    if not user_permissions:
        return False
    if '*' in user_permissions:
        return True
    return required_permission in user_permissions
