from typing import Optional, Dict, Any, List
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.crm.services.customer_communication_service import (
    CustomerCommunicationService,
    customer_communication_service,
)
from packages.mcp.registry import register_tool
from packages.mcp.types import Tool


_leads_repo = CrudRepository('T0092', business_columns=['id', 'first_name', 'last_name', 'email', 'phone', 'company', 'source', 'status', 'assigned_to', 'notes'])
_leads_svc = CrudService(_leads_repo)

_opps_repo = CrudRepository('T0094', business_columns=['id', 'opportunity_name', 'lead_id', 'customer_id', 'stage', 'amount', 'probability', 'expected_close_date', 'assigned_to', 'notes'])
_opps_svc = CrudService(_opps_repo)

_suppliers_repo = CrudRepository('T0011', business_columns=['id', 'name', 'category', 'phone', 'email', 'payment_terms', 'rating', 'is_active'])
_suppliers_svc = CrudService(_suppliers_repo)

_groups_repo = CrudRepository('T0102', business_columns=['id', 'name', 'is_active'])
_groups_svc = CrudService(_groups_repo)

_comm_svc = customer_communication_service


def register_tools():
    register_tool(Tool(name="list_leads", description="List sales leads", input_schema={
        "type": "object", "properties": {
            "status": {"type": "string"}, "assigned_to": {"type": "integer"},
            "limit": {"type": "integer"},
        },
    }), _list_leads)
    register_tool(Tool(name="list_opportunities", description="List sales opportunities", input_schema={
        "type": "object", "properties": {
            "stage": {"type": "string"}, "customer_id": {"type": "integer"},
            "limit": {"type": "integer"},
        },
    }), _list_opps)
    register_tool(Tool(name="list_suppliers", description="List suppliers", input_schema={
        "type": "object", "properties": {
            "category": {"type": "string"}, "limit": {"type": "integer"},
        },
    }), _list_suppliers)
    register_tool(Tool(name="list_customer_groups", description="List customer groups", input_schema={
        "type": "object", "properties": {},
    }), _list_groups)
    register_tool(
        Tool(
            name="list_customer_communications",
            description="List customer communication timeline records, dispatch logs, delivery statuses, and read receipts across Email and WhatsApp",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Optional customer ID to get customer-specific timeline"},
                    "channel": {"type": "string", "description": "Filter by channel ('EMAIL', 'WHATSAPP')"},
                    "status": {"type": "string", "description": "Filter by status ('PENDING', 'SENT', 'DELIVERED', 'READ', 'FAILED')"},
                    "communication_type": {"type": "string", "description": "Filter by communication type ('REMINDER', 'STATEMENT', 'CUSTOM')"},
                    "limit": {"type": "integer", "description": "Max results (default 50)"},
                },
            },
        ),
        _list_customer_communications,
    )


def _list_leads(status: str = None, assigned_to: int = None, limit: int = 50):
    filters = {}
    if status: filters["status"] = status
    if assigned_to: filters["assigned_to"] = assigned_to
    return _leads_svc.list(filters=filters or None, limit=limit)

def _list_opps(stage: str = None, customer_id: int = None, limit: int = 50):
    filters = {}
    if stage: filters["stage"] = stage
    if customer_id: filters["customer_id"] = customer_id
    return _opps_svc.list(filters=filters or None, limit=limit)

def _list_suppliers(category: str = None, limit: int = 50):
    filters = {}
    if category: filters["category"] = category
    return _suppliers_svc.list(filters=filters or None, limit=limit)

def _list_groups():
    return _groups_svc.list()

def _list_customer_communications(
    customer_id: Optional[int] = None,
    channel: Optional[str] = None,
    status: Optional[str] = None,
    communication_type: Optional[str] = None,
    limit: int = 50,
):
    if customer_id is not None:
        return _comm_svc.get_customer_timeline(
            customer_id=customer_id,
            channel=channel,
            status=status,
            communication_type=communication_type,
            limit=limit,
        )
    return _comm_svc.list_timeline(
        filters={
            k: v for k, v in [
                ("channel", channel),
                ("status", status),
                ("communication_type", communication_type),
            ] if v is not None
        } or None,
        limit=limit,
    )


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="crm-mcp", version="1.0"))

if __name__ == "__main__":
    main()
