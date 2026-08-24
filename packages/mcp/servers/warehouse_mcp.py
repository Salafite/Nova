from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.warehouse.services.batch_number_service import BatchNumberService
from modules.warehouse.services.pick_list_service import PickListService, PL_REPO, PLI_REPO
from packages.mcp.registry import register_tool, register_resource
from packages.mcp.types import Tool, Resource


_gr_repo = CrudRepository('T0075', business_columns=['id', 'receipt_number', 'purchase_order_id', 'receipt_date', 'warehouse_id', 'status', 'notes'])
_gr_svc = CrudService(_gr_repo)

_serial_repo = CrudRepository('T0087', business_columns=['id', 'product_id', 'serial_number', 'status', 'warehouse_id', 'notes'])
_serial_svc = CrudService(_serial_repo)

_batch_repo = CrudRepository('T0088', business_columns=['id', 'product_id', 'batch_number', 'expiry_date', 'manufacturing_date', 'quantity', 'warehouse_id', 'status', 'notes'])
_batch_svc = BatchNumberService(_batch_repo)

_pick_repo = PL_REPO
_pick_svc = PickListService(repo=_pick_repo, pli_repo=PLI_REPO)


def register_tools():
    register_tool(Tool(name="list_goods_receipts", description="List goods receipts", input_schema={
        "type": "object", "properties": {
            "status": {"type": "string"}, "purchase_order_id": {"type": "integer"},
            "limit": {"type": "integer"},
        },
    }), _list_gr)
    register_tool(Tool(name="list_serial_numbers", description="List serial numbers for a product", input_schema={
        "type": "object", "properties": {
            "product_id": {"type": "integer"}, "status": {"type": "string"},
            "warehouse_id": {"type": "integer"}, "limit": {"type": "integer"},
        },
    }), _list_serial)
    register_tool(Tool(name="list_batch_numbers", description="List batch numbers for a product", input_schema={
        "type": "object", "properties": {
            "product_id": {"type": "integer"}, "status": {"type": "string"},
            "warehouse_id": {"type": "integer"}, "limit": {"type": "integer"},
        },
    }), _list_batch)
    register_tool(Tool(name="list_pick_lists", description="List pick lists", input_schema={
        "type": "object", "properties": {
            "status": {"type": "string"}, "sales_order_id": {"type": "integer"},
            "limit": {"type": "integer"},
        },
    }), _list_pick)
    register_tool(Tool(name="get_pick_list", description="Get pick list details by ID with line items, scale weights, and catch-weight tolerance statuses", input_schema={
        "type": "object", "properties": {
            "id": {"type": "integer", "description": "Pick list ID"},
        },
        "required": ["id"],
    }), _get_pick_list)
    register_tool(Tool(name="pick_item", description="Pick a warehouse item and capture actual physical scale weight with automatic tolerance calculation", input_schema={
        "type": "object", "properties": {
            "item_id": {"type": "integer", "description": "Pick list item ID"},
            "qty_picked": {"type": "number", "description": "Quantity picked"},
            "pick_list_id": {"type": "integer", "description": "Pick list ID (optional)"},
            "catch_weight_actual": {"type": "number", "description": "Actual physical scale weight measured during picking"},
            "catch_weight_uom": {"type": "string", "description": "Catch-weight unit of measure (e.g. kg, lbs)"},
            "nominal_weight": {"type": "number", "description": "Expected nominal weight"},
            "tolerance_pct": {"type": "number", "description": "Allowable weight variance percentage (+/- %)"},
            "picked_batch_id": {"type": "integer", "description": "Picked batch record ID"},
            "picked_batch_number": {"type": "string", "description": "Picked batch/lot number"},
        },
        "required": ["item_id", "qty_picked"],
    }), _pick_item)
    register_tool(Tool(name="approve_pick_tolerance", description="Approve catch-weight out-of-tolerance discrepancy for pick list items", input_schema={
        "type": "object", "properties": {
            "pick_list_id": {"type": "integer", "description": "Pick list ID"},
            "item_id": {"type": "integer", "description": "Specific pick list item ID to approve"},
            "item_ids": {"type": "array", "items": {"type": "integer"}, "description": "List of pick list item IDs to approve"},
            "supervisor_id": {"type": "integer", "description": "Supervisor user ID granting approval"},
            "supervisor_notes": {"type": "string", "description": "Approval reason or notes"},
        },
        "required": ["pick_list_id"],
    }), _approve_pick_tolerance)
    register_tool(Tool(name="check_pick_list_discrepancies", description="Check for unapproved catch-weight tolerance discrepancies in a pick list", input_schema={
        "type": "object", "properties": {
            "pick_list_id": {"type": "integer", "description": "Pick list ID"},
        },
        "required": ["pick_list_id"],
    }), _check_pick_list_discrepancies)
    register_tool(Tool(name="get_batch_recall_report", description="Generate a food safety recall and lot traceability report for a batch/lot number, identifying inbound suppliers, warehouse stock, and outbound customer shipments.", input_schema={
        "type": "object", "properties": {
            "batch_number": {"type": "string", "description": "Batch / lot number to trace"},
            "batch_id": {"type": "integer", "description": "Optional batch record ID"},
            "product_id": {"type": "integer", "description": "Optional product ID filter"},
        },
    }), _get_batch_recall_report)
    register_resource(
        Resource(uri="nova://warehouse/pick-lists", name="All Pick Lists", description="List of all warehouse pick lists"),
        _list_pick,
    )


def _list_gr(status: str = None, purchase_order_id: int = None, limit: int = 50):
    filters = {}
    if status: filters["status"] = status
    if purchase_order_id: filters["purchase_order_id"] = purchase_order_id
    return _gr_svc.list(filters=filters or None, limit=limit)

def _list_serial(product_id: int = None, status: str = None, warehouse_id: int = None, limit: int = 50):
    filters = {}
    if product_id: filters["product_id"] = product_id
    if status: filters["status"] = status
    if warehouse_id: filters["warehouse_id"] = warehouse_id
    return _serial_svc.list(filters=filters or None, limit=limit)

def _list_batch(product_id: int = None, status: str = None, warehouse_id: int = None, limit: int = 50):
    filters = {}
    if product_id: filters["product_id"] = product_id
    if status: filters["status"] = status
    if warehouse_id: filters["warehouse_id"] = warehouse_id
    return _batch_svc.list(filters=filters or None, limit=limit)

def _list_pick(status: str = None, sales_order_id: int = None, limit: int = 50):
    filters = {}
    if status: filters["status"] = status
    if sales_order_id: filters["sales_order_id"] = sales_order_id
    return _pick_svc.list(filters=filters or None, limit=limit)

def _get_pick_list(id: int):
    if hasattr(_pick_svc, 'get_with_items'):
        return _pick_svc.get_with_items(id)
    return _pick_svc.get(id)

def _pick_item(
    item_id: int,
    qty_picked: float,
    pick_list_id: int = None,
    catch_weight_actual: float = None,
    catch_weight_uom: str = None,
    nominal_weight: float = None,
    tolerance_pct: float = None,
    picked_batch_id: int = None,
    picked_batch_number: str = None,
):
    return _pick_svc.pick_item(
        item_id=item_id,
        qty_picked=qty_picked,
        pick_list_id=pick_list_id,
        catch_weight_actual=catch_weight_actual,
        catch_weight_uom=catch_weight_uom,
        nominal_weight=nominal_weight,
        tolerance_pct=tolerance_pct,
        picked_batch_id=picked_batch_id,
        picked_batch_number=picked_batch_number,
    )

def _approve_pick_tolerance(
    pick_list_id: int,
    item_id: int = None,
    item_ids: list = None,
    supervisor_id: int = None,
    supervisor_notes: str = None,
):
    return _pick_svc.approve_tolerance(
        pick_list_id=pick_list_id,
        item_id=item_id,
        item_ids=item_ids,
        supervisor_id=supervisor_id,
        supervisor_notes=supervisor_notes,
    )

def _check_pick_list_discrepancies(pick_list_id: int):
    return _pick_svc.check_pick_list_discrepancies(pick_list_id)

def _get_batch_recall_report(batch_number: str = None, batch_id: int = None, product_id: int = None):
    if not batch_number and not batch_id:
        return {"error": "Either batch_number or batch_id must be provided"}
    try:
        return _batch_svc.get_recall_report(batch_number=batch_number, batch_id=batch_id, product_id=product_id)
    except Exception as e:
        return {"error": str(e)}


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="warehouse-mcp", version="1.0"))

if __name__ == "__main__":
    main()

