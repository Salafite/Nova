from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.warehouse.services.batch_number_service import BatchNumberService
from modules.warehouse.services.pick_list_service import PickListService, PL_REPO, PLI_REPO
from modules.warehouse.services.stock_transfer_service import (
    StockTransferService,
    TRANSFER_REPO,
    TRANSFER_LINE_REPO,
)
from modules.inventory.services.barcode_service import parse_barcode_string, find_product_by_barcode
from packages.database.connection import get_connection, release_connection
from modules.core.context import get_current_tenant
from packages.mcp.registry import register_tool, register_resource
from packages.mcp.types import Tool, Resource


_products_repo = CrudRepository('T0003', business_columns=['id', 'name', 'sku', 'barcode', 'description', 'price', 'is_active', 'is_catch_weight', 'nominal_weight', 'tolerance_pct'])
_products_svc = CrudService(_products_repo)

_gr_repo = CrudRepository('T0075', business_columns=['id', 'receipt_number', 'purchase_order_id', 'receipt_date', 'warehouse_id', 'status', 'notes'])
_gr_svc = CrudService(_gr_repo)

_serial_repo = CrudRepository('T0087', business_columns=['id', 'product_id', 'serial_number', 'status', 'warehouse_id', 'notes'])
_serial_svc = CrudService(_serial_repo)

_batch_repo = CrudRepository('T0088', business_columns=['id', 'product_id', 'batch_number', 'expiry_date', 'manufacturing_date', 'quantity', 'warehouse_id', 'status', 'notes'])
_batch_svc = BatchNumberService(_batch_repo)

_pick_repo = PL_REPO
_pick_svc = PickListService(repo=_pick_repo, pli_repo=PLI_REPO)

_transfer_repo = TRANSFER_REPO
_transfer_line_repo = TRANSFER_LINE_REPO
_transfer_svc = StockTransferService(repo=_transfer_repo, line_repo=_transfer_line_repo)


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
    register_tool(Tool(name="list_stock_transfers", description="List stock transfers with line summaries, with optional filtering by status or warehouse", input_schema={
        "type": "object", "properties": {
            "status": {"type": "string", "description": "Filter by status: Draft, In Transit, Received, Partially Received, Cancelled"},
            "source_warehouse_id": {"type": "integer", "description": "Filter by source warehouse ID"},
            "destination_warehouse_id": {"type": "integer", "description": "Filter by destination warehouse ID"},
            "limit": {"type": "integer", "description": "Maximum records to return (default 50)"},
            "offset": {"type": "integer", "description": "Offset for pagination (default 0)"},
        },
    }), _list_stock_transfers)
    register_tool(Tool(name="get_stock_transfer", description="Get stock transfer details by ID including itemized lines, quantities, and warehouse info", input_schema={
        "type": "object", "properties": {
            "id": {"type": "integer", "description": "Stock transfer ID"},
        },
        "required": ["id"],
    }), _get_stock_transfer)
    register_tool(Tool(name="create_stock_transfer", description="Create a new multi-warehouse stock transfer order with line items in Draft status", input_schema={
        "type": "object", "properties": {
            "source_warehouse_id": {"type": "integer", "description": "Source warehouse ID"},
            "destination_warehouse_id": {"type": "integer", "description": "Destination warehouse ID"},
            "lines": {
                "type": "array",
                "description": "Itemized transfer line items",
                "items": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer", "description": "Product ID"},
                        "qty_requested": {"type": "number", "description": "Requested quantity to transfer"},
                        "batch_id": {"type": "integer", "description": "Optional source batch ID"},
                        "batch_number": {"type": "string", "description": "Optional batch/lot number"},
                        "notes": {"type": "string", "description": "Line notes"},
                    },
                    "required": ["product_id", "qty_requested"],
                },
            },
            "transfer_number": {"type": "string", "description": "Optional transfer order number"},
            "transfer_date": {"type": "string", "description": "Transfer date (YYYY-MM-DD)"},
            "expected_delivery_date": {"type": "string", "description": "Expected delivery date (YYYY-MM-DD)"},
            "carrier": {"type": "string", "description": "Logistics carrier name"},
            "tracking_number": {"type": "string", "description": "Carrier tracking number"},
            "notes": {"type": "string", "description": "Transfer header notes"},
        },
        "required": ["source_warehouse_id", "destination_warehouse_id", "lines"],
    }), _create_stock_transfer)
    register_tool(Tool(name="dispatch_stock_transfer", description="Dispatch a stock transfer from source warehouse into in-transit status, deducting source stock and incrementing destination in-transit quantity", input_schema={
        "type": "object", "properties": {
            "id": {"type": "integer", "description": "Stock transfer ID"},
            "transfer_id": {"type": "integer", "description": "Alternative stock transfer ID parameter"},
            "carrier": {"type": "string", "description": "Logistics carrier name"},
            "tracking_number": {"type": "string", "description": "Carrier tracking number"},
            "dispatched_by": {"type": "integer", "description": "User ID performing dispatch"},
            "dispatched_at": {"type": "string", "description": "Dispatch timestamp (ISO format)"},
            "notes": {"type": "string", "description": "Dispatch notes"},
            "lines": {
                "type": "array",
                "description": "Itemized line dispatch quantities (optional; defaults to requested quantities)",
                "items": {
                    "type": "object",
                    "properties": {
                        "line_id": {"type": "integer", "description": "Transfer line ID"},
                        "qty_dispatched": {"type": "number", "description": "Actual dispatched quantity"},
                        "batch_id": {"type": "integer", "description": "Batch ID"},
                        "batch_number": {"type": "string", "description": "Batch number"},
                    },
                },
            },
        },
    }), _dispatch_stock_transfer)
    register_tool(Tool(name="receive_stock_transfer", description="Receive a stock transfer at destination warehouse, moving items from in-transit to available inventory and logging any transit loss/damage discrepancies", input_schema={
        "type": "object", "properties": {
            "id": {"type": "integer", "description": "Stock transfer ID"},
            "transfer_id": {"type": "integer", "description": "Alternative stock transfer ID parameter"},
            "received_by": {"type": "integer", "description": "User ID receiving items"},
            "received_at": {"type": "string", "description": "Receipt timestamp (ISO format)"},
            "notes": {"type": "string", "description": "Receipt notes"},
            "lines": {
                "type": "array",
                "description": "Itemized line receipt quantities and discrepancy details",
                "items": {
                    "type": "object",
                    "properties": {
                        "line_id": {"type": "integer", "description": "Transfer line ID"},
                        "qty_received": {"type": "number", "description": "Actual received quantity"},
                        "qty_lost": {"type": "number", "description": "Quantity lost or damaged in transit"},
                        "loss_reason": {"type": "string", "description": "Discrepancy / loss reason code (e.g. Damage, Theft, Expired, Missing, Spillage)"},
                        "loss_notes": {"type": "string", "description": "Discrepancy notes"},
                        "batch_id": {"type": "integer", "description": "Batch ID"},
                        "batch_number": {"type": "string", "description": "Batch number"},
                    },
                },
            },
            "losses": {
                "type": "array",
                "description": "Optional loss / damage discrepancy records",
                "items": {
                    "type": "object",
                    "properties": {
                        "line_id": {"type": "integer"},
                        "product_id": {"type": "integer"},
                        "qty_lost": {"type": "number"},
                        "loss_reason": {"type": "string"},
                        "loss_notes": {"type": "string"},
                    },
                },
            },
        },
    }), _receive_stock_transfer)
    register_tool(Tool(name="verify_barcode", description="Parse and verify a raw barcode string (EAN-13, UPC-A, Code 128, GS1-128) against the product master catalog and return parsed GS1 metadata (GTIN, batch, expiry, serial) along with matching product details.", input_schema={
        "type": "object", "properties": {
            "barcode": {"type": "string", "description": "Scanned raw barcode string (EAN-13, UPC-A, Code 128, GS1-128)"},
        },
        "required": ["barcode"],
    }), _verify_barcode)
    register_tool(Tool(name="verify_pick_barcode", description="Verify a scanned barcode against a warehouse pick list to confirm item matching, validate batch/lot numbers against allocated FEFO batches, check expiry, and verify quantities.", input_schema={
        "type": "object", "properties": {
            "pick_list_id": {"type": "integer", "description": "Pick list ID"},
            "barcode": {"type": "string", "description": "Scanned raw barcode string"},
            "qty": {"type": "number", "description": "Quantity scanned or picked (default 1.0)"},
        },
        "required": ["pick_list_id", "barcode"],
    }), _verify_pick_barcode)
    register_tool(Tool(name="verify_goods_receipt_barcode", description="Verify a scanned barcode for inbound goods receiving, matching against goods receipt or purchase order lines, extracting GS1-128 batch and expiry metadata, and validating receiving quantities.", input_schema={
        "type": "object", "properties": {
            "barcode": {"type": "string", "description": "Scanned raw barcode string"},
            "receipt_id": {"type": "integer", "description": "Goods receipt ID (optional)"},
            "purchase_order_id": {"type": "integer", "description": "Purchase order ID (optional)"},
            "qty": {"type": "number", "description": "Quantity received (default 1.0)"},
        },
        "required": ["barcode"],
    }), _verify_goods_receipt_barcode)
    register_resource(
        Resource(uri="nova://warehouse/pick-lists", name="All Pick Lists", description="List of all warehouse pick lists"),
        _list_pick,
    )
    register_resource(
        Resource(uri="nova://warehouse/stock-transfers", name="All Stock Transfers", description="List of all stock transfers and inter-warehouse shipments"),
        _list_stock_transfers,
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

_list_pick_lists = _list_pick


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


def _list_stock_transfers(
    status: str = None,
    source_warehouse_id: int = None,
    destination_warehouse_id: int = None,
    limit: int = 50,
    offset: int = 0,
):
    filters = {}
    if status:
        filters["status"] = status
    if source_warehouse_id:
        filters["source_warehouse_id"] = source_warehouse_id
    if destination_warehouse_id:
        filters["destination_warehouse_id"] = destination_warehouse_id
    if hasattr(_transfer_svc, 'list_with_lines'):
        return _transfer_svc.list_with_lines(filters=filters or None, limit=limit, offset=offset)
    return _transfer_svc.list(filters=filters or None, limit=limit, offset=offset)


def _get_stock_transfer(id: int):
    if hasattr(_transfer_svc, 'get_transfer_with_lines'):
        return _transfer_svc.get_transfer_with_lines(id)
    return _transfer_svc.get(id)


def _create_stock_transfer(
    source_warehouse_id: int,
    destination_warehouse_id: int,
    lines: list = None,
    items: list = None,
    transfer_number: str = None,
    transfer_date: str = None,
    expected_delivery_date: str = None,
    carrier: str = None,
    tracking_number: str = None,
    notes: str = None,
    **kwargs,
):
    transfer_lines = lines if lines is not None else (items or [])
    payload = {
        "source_warehouse_id": source_warehouse_id,
        "destination_warehouse_id": destination_warehouse_id,
        "lines": transfer_lines,
    }
    if transfer_number:
        payload["transfer_number"] = transfer_number
    if transfer_date:
        payload["transfer_date"] = transfer_date
    if expected_delivery_date:
        payload["expected_delivery_date"] = expected_delivery_date
    if carrier:
        payload["carrier"] = carrier
    if tracking_number:
        payload["tracking_number"] = tracking_number
    if notes:
        payload["notes"] = notes
    for k, v in kwargs.items():
        if v is not None and k not in payload:
            payload[k] = v
    if hasattr(_transfer_svc, 'create_transfer'):
        return _transfer_svc.create_transfer(payload)
    return _transfer_svc.create(payload)


def _dispatch_stock_transfer(
    id: int = None,
    transfer_id: int = None,
    carrier: str = None,
    tracking_number: str = None,
    dispatched_by: int = None,
    dispatched_at: str = None,
    notes: str = None,
    lines: list = None,
    **kwargs,
):
    target_id = id or transfer_id or kwargs.get("transfer_order_id")
    if not target_id:
        raise ValueError("Transfer ID (id or transfer_id) is required")
    dispatch_data = {}
    if carrier:
        dispatch_data["carrier"] = carrier
    if tracking_number:
        dispatch_data["tracking_number"] = tracking_number
    if dispatched_by:
        dispatch_data["dispatched_by"] = dispatched_by
    if dispatched_at:
        dispatch_data["dispatched_at"] = dispatched_at
    if notes:
        dispatch_data["notes"] = notes
    if lines is not None:
        dispatch_data["lines"] = lines
    for k, v in kwargs.items():
        if v is not None and k not in dispatch_data:
            dispatch_data[k] = v
    return _transfer_svc.dispatch_transfer(target_id, dispatch_data=dispatch_data or None)


def _receive_stock_transfer(
    id: int = None,
    transfer_id: int = None,
    received_by: int = None,
    received_at: str = None,
    notes: str = None,
    lines: list = None,
    losses: list = None,
    **kwargs,
):
    target_id = id or transfer_id or kwargs.get("transfer_order_id")
    if not target_id:
        raise ValueError("Transfer ID (id or transfer_id) is required")
    receive_data = {}
    if received_by:
        receive_data["received_by"] = received_by
    if received_at:
        receive_data["received_at"] = received_at
    if notes:
        receive_data["notes"] = notes
    if lines is not None:
        receive_data["lines"] = lines
    if losses is not None:
        receive_data["losses"] = losses
    for k, v in kwargs.items():
        if v is not None and k not in receive_data:
            receive_data[k] = v
    return _transfer_svc.receive_transfer(target_id, receive_data=receive_data or None)


def _verify_barcode(barcode: str):
    if not barcode:
        return {"valid": False, "error": "Barcode string is required"}
    parsed = parse_barcode_string(barcode)
    product = None
    try:
        conn = get_connection()
        try:
            product = find_product_by_barcode(conn, barcode, tenant_id=get_current_tenant())
        finally:
            release_connection(conn)
    except Exception:
        product = None

    if not product and hasattr(_products_repo, 'list'):
        try:
            candidates = parsed.get("candidates", [])
            for cand in candidates:
                prods = _products_repo.list(filters={"barcode": cand}, limit=1)
                if not prods:
                    prods = _products_repo.list(filters={"sku": cand}, limit=1)
                if prods:
                    product = prods[0]
                    break
        except Exception:
            pass

    matched = product is not None
    prod_name = ""
    if matched:
        prod_name = product.get("name") if isinstance(product, dict) else getattr(product, "name", "")
    return {
        "valid": matched,
        "matched": matched,
        "raw_barcode": barcode,
        "parsed_barcode": parsed,
        "product": product,
        "message": f"Barcode matched product '{prod_name}'" if matched else f"No product found matching barcode '{barcode}'"
    }


def _verify_pick_barcode(pick_list_id: int, barcode: str, qty: float = 1.0):
    if not pick_list_id or not barcode:
        return {"valid": False, "error": "pick_list_id and barcode are required"}
    
    pick_list = _get_pick_list(pick_list_id)
    if not pick_list or (isinstance(pick_list, dict) and "error" in pick_list):
        return {"valid": False, "error": f"Pick list #{pick_list_id} not found"}

    verification = _verify_barcode(barcode)
    parsed = verification.get("parsed_barcode", parse_barcode_string(barcode))
    product = verification.get("product")
    candidates = parsed.get("candidates", [barcode])

    items = []
    if isinstance(pick_list, dict):
        items = pick_list.get("items", []) or pick_list.get("lines", [])
    elif hasattr(pick_list, "items"):
        items = pick_list.items

    matched_item = None
    for item in items:
        item_dict = item if isinstance(item, dict) else (item.to_dict() if hasattr(item, "to_dict") else vars(item))
        prod_id = product.get("id") if isinstance(product, dict) else getattr(product, "id", None) if product else None
        if prod_id and (item_dict.get("product_id") == prod_id):
            matched_item = item_dict
            break
        item_barcode = str(item_dict.get("barcode") or item_dict.get("gtin") or "").strip()
        item_sku = str(item_dict.get("product_sku") or item_dict.get("sku") or "").strip()
        if (item_barcode and item_barcode in candidates) or (item_sku and item_sku in candidates):
            matched_item = item_dict
            break

    if not matched_item:
        return {
            "valid": False,
            "matched": False,
            "pick_list_id": pick_list_id,
            "raw_barcode": barcode,
            "parsed_barcode": parsed,
            "product": product,
            "error": f"Scanned barcode '{barcode}' does not match any item on pick list #{pick_list_id}",
            "message": f"Barcode rejection: Product not found in pick list #{pick_list_id}"
        }

    batch_number = parsed.get("batch_number")
    expiry_date = parsed.get("expiry_date")
    batch_valid = True
    batch_warning = None
    
    allocated_batch = matched_item.get("allocated_batch_number") or matched_item.get("batch_number")
    if batch_number and allocated_batch:
        if batch_number != allocated_batch:
            batch_valid = False
            batch_warning = f"Scanned batch '{batch_number}' does not match allocated FEFO batch '{allocated_batch}'"

    is_expired = False
    if expiry_date:
        try:
            from datetime import datetime
            exp_str = str(expiry_date)
            if len(exp_str) == 6 and exp_str.isdigit():
                exp_year = int("20" + exp_str[:2])
                exp_month = int(exp_str[2:4])
                exp_day = int(exp_str[4:6])
                exp_dt = datetime(exp_year, exp_month, exp_day, 23, 59, 59)
            elif "-" in exp_str:
                exp_dt = datetime.strptime(exp_str[:10], "%Y-%m-%d")
            else:
                exp_dt = None
            if exp_dt and exp_dt < datetime.now():
                is_expired = True
        except Exception:
            pass

    qty_ordered = float(matched_item.get("qty_ordered") or matched_item.get("quantity") or 0)
    qty_picked = float(matched_item.get("qty_picked") or 0)
    remaining_qty = max(0.0, qty_ordered - qty_picked)
    over_picked = (qty_picked + qty) > qty_ordered

    prod_name = matched_item.get("product_name") or (product.get("name") if isinstance(product, dict) else getattr(product, "name", "")) if product else "Item"
    return {
        "valid": True,
        "matched": True,
        "pick_list_id": pick_list_id,
        "item_id": matched_item.get("id"),
        "item": matched_item,
        "raw_barcode": barcode,
        "parsed_barcode": parsed,
        "product": product,
        "qty_scanned": qty,
        "qty_picked": qty_picked,
        "qty_ordered": qty_ordered,
        "remaining_qty": remaining_qty,
        "over_picked": over_picked,
        "batch_number": batch_number,
        "allocated_batch_number": allocated_batch,
        "batch_matched": batch_valid,
        "batch_warning": batch_warning,
        "is_expired": is_expired,
        "message": f"Valid pick scan for product '{prod_name}'"
    }


def _verify_goods_receipt_barcode(barcode: str, receipt_id: int = None, purchase_order_id: int = None, qty: float = 1.0):
    if not barcode:
        return {"valid": False, "error": "Barcode string is required"}
    
    verification = _verify_barcode(barcode)
    parsed = verification.get("parsed_barcode", parse_barcode_string(barcode))
    product = verification.get("product")
    candidates = parsed.get("candidates", [barcode])

    receipt = None
    lines = []
    if receipt_id:
        if hasattr(_gr_svc, "get_with_items"):
            receipt = _gr_svc.get_with_items(receipt_id)
        else:
            receipt = _gr_svc.get(receipt_id)
        if isinstance(receipt, dict):
            lines = receipt.get("items", []) or receipt.get("lines", [])
    
    matched_line = None
    if lines:
        for line in lines:
            line_dict = line if isinstance(line, dict) else (line.to_dict() if hasattr(line, "to_dict") else vars(line))
            prod_id = product.get("id") if isinstance(product, dict) else getattr(product, "id", None) if product else None
            if prod_id and line_dict.get("product_id") == prod_id:
                matched_line = line_dict
                break
            line_barcode = str(line_dict.get("barcode") or "").strip()
            line_sku = str(line_dict.get("product_sku") or line_dict.get("sku") or "").strip()
            if (line_barcode and line_barcode in candidates) or (line_sku and line_sku in candidates):
                matched_line = line_dict
                break

    prod_name = (product.get("name") if isinstance(product, dict) else getattr(product, "name", "")) if product else barcode
    return {
        "valid": product is not None,
        "matched": product is not None and (not receipt_id or matched_line is not None),
        "receipt_id": receipt_id,
        "purchase_order_id": purchase_order_id,
        "raw_barcode": barcode,
        "parsed_barcode": parsed,
        "product": product,
        "matched_line": matched_line,
        "extracted_batch_number": parsed.get("batch_number"),
        "extracted_expiry_date": parsed.get("expiry_date"),
        "extracted_serial_number": parsed.get("serial_number"),
        "qty_scanned": qty,
        "message": f"Goods receipt barcode scan verified for '{prod_name}'" if product else f"Unrecognized goods receipt barcode '{barcode}'"
    }


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="warehouse-mcp", version="1.0"))

if __name__ == "__main__":
    main()

