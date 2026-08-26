import psycopg2.extras
from modules.core.context import get_current_tenant
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.inventory.services.replenishment_service import ReplenishmentService
from packages.database.connection import get_connection, release_connection
from packages.mcp.registry import register_tool, register_resource, get_current_user
from packages.mcp.types import Tool, Resource


_products_repo = CrudRepository('T0003', business_columns=[
    'id', 'name', 'sku', 'barcode', 'description', 'type', 'price', 'cost_price',
    'category', 'brand', 'tax_rate', 'weight', 'volume', 'image_url',
    'is_purchasable', 'is_saleable', 'is_active',
    'is_catch_weight', 'pricing_uom_id', 'nominal_weight', 'tolerance_pct', 'pricing_basis'
])
_products_svc = CrudService(_products_repo)

_categories_repo = CrudRepository('T0005', business_columns=['id', 'attribute_name', 'is_active'])
_categories_svc = CrudService(_categories_repo)

_warehouses_repo = CrudRepository('T0008', business_columns=['id', 'name', 'location', 'is_active'])
_warehouses_svc = CrudService(_warehouses_repo)

_uoms_repo = CrudRepository('T0001', business_columns=['id', 'uom_code', 'uom_name', 'category', 'is_base_unit', 'is_active'])
_uoms_svc = CrudService(_uoms_repo)

_brands_repo = CrudRepository('T0051', business_columns=['id', 'name', 'is_active'])
_brands_svc = CrudService(_brands_repo)

_stock_repo = CrudRepository('T0009', business_columns=['id', 'product_id', 'warehouse_id', 'qty', 'reserved_qty', 'reorder_level'])
_stock_svc = CrudService(_stock_repo)

_replenishment_svc = ReplenishmentService()


def register_tools():
    register_tool(
        Tool(name="list_products", description="List all products with optional filters", input_schema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Filter by category"},
                "brand": {"type": "string", "description": "Filter by brand"},
                "is_catch_weight": {"type": "boolean", "description": "Filter by catch weight products"},
                "limit": {"type": "integer", "description": "Max results (default 50)"},
                "offset": {"type": "integer", "description": "Offset for pagination"},
            },
        }),
        _list_products,
    )
    register_tool(
        Tool(name="get_product", description="Get a single product by ID", input_schema={
            "type": "object",
            "properties": {"id": {"type": "integer", "description": "Product ID"}},
            "required": ["id"],
        }),
        _get_product,
    )
    register_tool(
        Tool(name="create_product", description="Create a new product", input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Product name"},
                "sku": {"type": "string", "description": "SKU code"},
                "barcode": {"type": "string", "description": "Product barcode / EAN / UPC"},
                "description": {"type": "string", "description": "Product description"},
                "type": {"type": "string", "description": "Product type: stockable, consumable, service (default stockable)"},
                "price": {"type": "number", "description": "Selling price"},
                "cost_price": {"type": "number", "description": "Cost price"},
                "category": {"type": "string", "description": "Category name"},
                "brand": {"type": "string", "description": "Brand name"},
                "tax_rate": {"type": "number", "description": "Tax rate (default 0.05)"},
                "weight": {"type": "number", "description": "Weight in kg"},
                "volume": {"type": "number", "description": "Volume in m3"},
                "image_url": {"type": "string", "description": "Product image URL"},
                "is_purchasable": {"type": "boolean", "description": "Can be purchased (default true)"},
                "is_saleable": {"type": "boolean", "description": "Can be sold (default true)"},
                "is_active": {"type": "boolean", "description": "Active status (default true)"},
                "is_catch_weight": {"type": "boolean", "description": "Flag indicating product is priced by catch-weight (variable weight)"},
                "pricing_uom_id": {"type": "integer", "description": "Pricing unit of measure ID (e.g. kg/lbs)"},
                "nominal_weight": {"type": "number", "description": "Expected nominal weight per stocking unit"},
                "tolerance_pct": {"type": "number", "description": "Allowable weight variance percentage (+/- %)"},
                "pricing_basis": {"type": "string", "description": "Pricing basis: 'weight' or 'unit' (default weight)"},
            },
            "required": ["name", "sku"],
        }),
        _create_product,
    )
    register_tool(
        Tool(name="update_product", description="Update an existing product", input_schema={
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Product ID"},
                "name": {"type": "string"},
                "sku": {"type": "string"},
                "barcode": {"type": "string"},
                "description": {"type": "string"},
                "type": {"type": "string"},
                "price": {"type": "number"},
                "cost_price": {"type": "number"},
                "category": {"type": "string"},
                "brand": {"type": "string"},
                "tax_rate": {"type": "number"},
                "weight": {"type": "number"},
                "volume": {"type": "number"},
                "image_url": {"type": "string"},
                "is_purchasable": {"type": "boolean"},
                "is_saleable": {"type": "boolean"},
                "is_active": {"type": "boolean"},
                "is_catch_weight": {"type": "boolean", "description": "Flag indicating product is priced by catch-weight"},
                "pricing_uom_id": {"type": "integer", "description": "Pricing unit of measure ID"},
                "nominal_weight": {"type": "number", "description": "Expected nominal weight per stocking unit"},
                "tolerance_pct": {"type": "number", "description": "Allowable weight variance percentage (+/- %)"},
                "pricing_basis": {"type": "string", "description": "Pricing basis: 'weight' or 'unit'"},
            },
            "required": ["id"],
        }),
        _update_product,
    )
    register_tool(
        Tool(name="delete_product", description="Soft-delete a product", tier="tier2", input_schema={
            "type": "object",
            "properties": {"id": {"type": "integer", "description": "Product ID"}},
            "required": ["id"],
        }),
        _delete_product,
    )
    register_tool(
        Tool(name="search_products", description="Search products by name or SKU", input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term"},
                "limit": {"type": "integer", "description": "Max results (default 20)"},
            },
            "required": ["query"],
        }),
        _search_products,
    )
    register_tool(
        Tool(name="check_stock", description="Check stock level for a product in a warehouse", input_schema={
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "Product ID"},
                "warehouse_id": {"type": "integer", "description": "Warehouse ID (optional)"},
            },
            "required": ["product_id"],
        }),
        _check_stock,
    )
    register_tool(
        Tool(name="list_categories", description="List all product categories", input_schema={
            "type": "object", "properties": {},
        }),
        _list_categories,
    )
    register_tool(
        Tool(name="list_warehouses", description="List all warehouses", input_schema={
            "type": "object", "properties": {},
        }),
        _list_warehouses,
    )
    register_tool(
        Tool(name="list_uoms", description="List all units of measure", input_schema={
            "type": "object", "properties": {},
        }),
        _list_uoms,
    )
    register_tool(
        Tool(name="list_brands", description="List all brands", input_schema={
            "type": "object", "properties": {},
        }),
        _list_brands,
    )
    register_tool(
        Tool(name="list_replenishment_suggestions", description="List inter-branch replenishment suggestions evaluating warehouse inventory levels against reorder thresholds and safety stock, matching deficits with surplus central distribution hubs", input_schema={
            "type": "object",
            "properties": {
                "warehouse_id": {"type": "integer", "description": "Destination branch warehouse ID to evaluate"},
                "destination_warehouse_id": {"type": "integer", "description": "Alternative parameter for destination warehouse ID"},
                "source_warehouse_id": {"type": "integer", "description": "Preferred source hub warehouse ID"},
                "product_id": {"type": "integer", "description": "Filter to a specific product SKU"},
                "category": {"type": "string", "description": "Filter products by category"},
                "priority": {"type": "string", "description": "Filter by priority level ('Critical', 'High', 'Normal', 'Low')"},
                "min_deficit": {"type": "number", "description": "Minimum quantity deficit required (default 0.0)"},
                "safety_stock_ratio": {"type": "number", "description": "Ratio of reorder level used as safety threshold (default 0.5)"},
                "target_coverage_multiplier": {"type": "number", "description": "Multiplier on reorder level for target order size (default 1.5)"},
            },
        }),
        _list_replenishment_suggestions,
    )
    register_tool(
        Tool(name="generate_replenishment_transfers", description="Generate draft multi-warehouse Stock Transfer orders from replenishment recommendations, grouping items by source and destination warehouses", input_schema={
            "type": "object",
            "properties": {
                "destination_warehouse_id": {"type": "integer", "description": "Optional destination warehouse ID filter/target"},
                "source_warehouse_id": {"type": "integer", "description": "Optional source warehouse ID"},
                "items": {
                    "type": "array",
                    "description": "Itemized replenishment suggestions to convert into transfer orders (optional; if omitted, automatically generates transfers for all active suggestions)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "integer", "description": "Product ID"},
                            "destination_warehouse_id": {"type": "integer", "description": "Destination warehouse ID"},
                            "source_warehouse_id": {"type": "integer", "description": "Source warehouse ID"},
                            "suggested_transfer_qty": {"type": "number", "description": "Quantity to transfer"},
                            "batch_id": {"type": "integer", "description": "Optional batch record ID"},
                            "batch_number": {"type": "string", "description": "Optional batch/lot number"},
                        },
                        "required": ["product_id", "destination_warehouse_id", "source_warehouse_id", "suggested_transfer_qty"],
                    },
                },
                "transfer_date": {"type": "string", "description": "Transfer date (YYYY-MM-DD)"},
                "expected_delivery_date": {"type": "string", "description": "Expected delivery date (YYYY-MM-DD)"},
                "carrier": {"type": "string", "description": "Logistics carrier name"},
                "notes": {"type": "string", "description": "Transfer header notes"},
            },
        }),
        _generate_replenishment_transfers,
    )
    register_resource(
        Resource(uri="nova://inventory/products", name="All Products", description="List of all products"),
        _list_products,
    )
    register_resource(
        Resource(uri="nova://inventory/replenishment-suggestions", name="Replenishment Suggestions", description="List of inter-branch replenishment suggestions and inventory deficit recommendations"),
        _list_replenishment_suggestions,
    )


def _list_products(category: str = None, brand: str = None, is_catch_weight: bool = None, limit: int = 50, offset: int = 0):
    filters = {}
    if category:
        filters["category"] = category
    if brand:
        filters["brand"] = brand
    if is_catch_weight is not None:
        filters["is_catch_weight"] = is_catch_weight
    return _products_svc.list(filters=filters or None, limit=limit, offset=offset)


def _get_product(id: int):
    return _products_svc.get(id)


def _create_product(
    name: str,
    sku: str,
    barcode: str = None,
    description: str = None,
    type: str = "stockable",
    price: float = 0,
    cost_price: float = 0,
    category: str = None,
    brand: str = None,
    tax_rate: float = 0.05,
    weight: float = 0,
    volume: float = 0,
    image_url: str = None,
    is_purchasable: bool = True,
    is_saleable: bool = True,
    is_active: bool = True,
    is_catch_weight: bool = False,
    pricing_uom_id: int = None,
    nominal_weight: float = None,
    tolerance_pct: float = None,
    pricing_basis: str = "weight",
):
    return _products_svc.create({
        "name": name,
        "sku": sku,
        "barcode": barcode,
        "description": description,
        "type": type,
        "price": price,
        "cost_price": cost_price,
        "category": category,
        "brand": brand,
        "tax_rate": tax_rate,
        "weight": weight,
        "volume": volume,
        "image_url": image_url,
        "is_purchasable": is_purchasable,
        "is_saleable": is_saleable,
        "is_active": is_active,
        "is_catch_weight": is_catch_weight,
        "pricing_uom_id": pricing_uom_id,
        "nominal_weight": nominal_weight,
        "tolerance_pct": tolerance_pct,
        "pricing_basis": pricing_basis,
    })


def _update_product(id: int, **kwargs):
    payload = {k: v for k, v in kwargs.items() if v is not None and k != "id"}
    return _products_svc.update(id, payload)


def _delete_product(id: int):
    return _products_svc.delete(id)


def _search_products(query: str, limit: int = 20):
    conn = get_connection()
    try:
        tenant_id = get_current_tenant()
        pattern = f'%{query}%'
        if tenant_id is not None:
            sql = 'SELECT * FROM "Nova".t0003 WHERE is_active = TRUE AND business_id = %s AND (name ILIKE %s OR sku ILIKE %s) ORDER BY name LIMIT %s'
            params = (tenant_id, pattern, pattern, limit)
        else:
            sql = 'SELECT * FROM "Nova".t0003 WHERE is_active = TRUE AND (name ILIKE %s OR sku ILIKE %s) ORDER BY name LIMIT %s'
            params = (pattern, pattern, limit)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_connection(conn)


def _check_stock(product_id: int, warehouse_id: int = None):
    filters = {"product_id": product_id}
    if warehouse_id:
        filters["warehouse_id"] = warehouse_id
    results = _stock_svc.list(filters=filters)
    for r in results:
        r["available_qty"] = max(0, r.get("qty", 0) - r.get("reserved_qty", 0))
    return results


def _list_categories():
    return _categories_svc.list()


def _list_warehouses():
    return _warehouses_svc.list()


def _list_uoms():
    return _uoms_svc.list()


def _list_brands():
    return _brands_svc.list()


def _list_replenishment_suggestions(
    warehouse_id: int = None,
    destination_warehouse_id: int = None,
    source_warehouse_id: int = None,
    product_id: int = None,
    category: str = None,
    priority: str = None,
    min_deficit: float = 0.0,
    safety_stock_ratio: float = 0.5,
    target_coverage_multiplier: float = 1.5,
    **kwargs,
):
    target_wh = warehouse_id if warehouse_id is not None else destination_warehouse_id
    if hasattr(_replenishment_svc, "get_replenishment_suggestions"):
        return _replenishment_svc.get_replenishment_suggestions(
            warehouse_id=target_wh,
            source_warehouse_id=source_warehouse_id,
            product_id=product_id,
            category=category,
            priority=priority,
            min_deficit=min_deficit if min_deficit is not None else 0.0,
            safety_stock_ratio=safety_stock_ratio if safety_stock_ratio is not None else 0.5,
            target_coverage_multiplier=target_coverage_multiplier if target_coverage_multiplier is not None else 1.5,
        )
    return {"total_suggestions": 0, "items": []}


def _generate_replenishment_transfers(
    destination_warehouse_id: int = None,
    source_warehouse_id: int = None,
    items: list = None,
    suggestions: list = None,
    transfer_date: str = None,
    expected_delivery_date: str = None,
    carrier: str = None,
    notes: str = None,
    **kwargs,
):
    user = get_current_user()
    user_id = user.get("id") if isinstance(user, dict) else None
    transfer_items = items if items is not None else suggestions
    payload = {
        "destination_warehouse_id": destination_warehouse_id,
        "source_warehouse_id": source_warehouse_id,
        "items": transfer_items,
        "transfer_date": transfer_date,
        "expected_delivery_date": expected_delivery_date,
        "carrier": carrier,
        "notes": notes,
    }
    for k, v in kwargs.items():
        if v is not None and k not in payload:
            payload[k] = v
    if hasattr(_replenishment_svc, "generate_transfers"):
        return _replenishment_svc.generate_transfers(payload=payload, user_id=user_id)
    return {"transfers_created": 0, "transfers": []}


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    server = McpServer(name="inventory-mcp", version="1.0")
    run_stdio(server)


if __name__ == "__main__":
    main()
