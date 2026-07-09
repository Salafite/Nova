from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.mcp.registry import register_tool
from packages.mcp.types import Tool


_coa_repo = CrudRepository('T0026', business_columns=['id', 'account_code', 'account_name', 'account_type', 'parent_id', 'currency', 'is_active'])
_coa_svc = CrudService(_coa_repo)

_inv_repo = CrudRepository('T0090', business_columns=['id', 'invoice_number', 'invoice_type', 'partner_id', 'sales_order_id', 'issue_date', 'due_date', 'total_amount', 'status', 'notes'])
_inv_svc = CrudService(_inv_repo)

_pay_repo = CrudRepository('T0091', business_columns=['id', 'payment_date', 'invoice_id', 'partner_id', 'amount', 'payment_method', 'reference', 'status', 'notes'])
_pay_svc = CrudService(_pay_repo)

_terms_repo = CrudRepository('T0096', business_columns=['id', 'name', 'code', 'description', 'due_days', 'discount_percentage', 'discount_days', 'is_active'])
_terms_svc = CrudService(_terms_repo)


def register_tools():
    register_tool(Tool(name="list_chart_of_accounts", description="List chart of accounts", input_schema={
        "type": "object", "properties": {"account_type": {"type": "string"}, "limit": {"type": "integer"}},
    }), _list_coa)
    register_tool(Tool(name="list_invoices", description="List invoices", input_schema={
        "type": "object", "properties": {
            "status": {"type": "string"}, "partner_id": {"type": "integer"}, "invoice_type": {"type": "string"},
            "limit": {"type": "integer"},
        },
    }), _list_invoices)
    register_tool(Tool(name="get_invoice", description="Get invoice by ID", input_schema={
        "type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"],
    }), _get_invoice)
    register_tool(Tool(name="list_payments", description="List payments received", input_schema={
        "type": "object", "properties": {
            "partner_id": {"type": "integer"}, "status": {"type": "string"}, "limit": {"type": "integer"},
        },
    }), _list_payments)
    register_tool(Tool(name="list_payment_terms", description="List payment terms and methods", input_schema={
        "type": "object", "properties": {},
    }), _list_terms)


def _list_coa(account_type: str = None, limit: int = 100):
    filters = {}
    if account_type: filters["account_type"] = account_type
    return _coa_svc.list(filters=filters or None, limit=limit)

def _list_invoices(status: str = None, partner_id: int = None, invoice_type: str = None, limit: int = 50):
    filters = {}
    if status: filters["status"] = status
    if partner_id: filters["partner_id"] = partner_id
    if invoice_type: filters["invoice_type"] = invoice_type
    return _inv_svc.list(filters=filters or None, limit=limit)

def _get_invoice(id: int):
    return _inv_svc.get(id)

def _list_payments(partner_id: int = None, status: str = None, limit: int = 50):
    filters = {}
    if partner_id: filters["partner_id"] = partner_id
    if status: filters["status"] = status
    return _pay_svc.list(filters=filters or None, limit=limit)

def _list_terms():
    return _terms_svc.list()


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="accounting-mcp", version="1.0"))

if __name__ == "__main__":
    main()
