import psycopg2.extras
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.database.connection import get_connection, release_connection
from packages.mcp.registry import register_tool, register_resource
from packages.mcp.types import Tool, Resource


_products_repo = CrudRepository('T0005', business_columns=['id', 'name', 'sku', 'price', 'cost_price', 'category', 'brand', 'tax_rate', 'image_url', 'is_active'])
_products_svc = CrudService(_products_repo)

_categories_repo = CrudRepository('T0003', business_columns=['id', 'name', 'is_active'])
_categories_svc = CrudService(_categories_repo)

_warehouses_repo = CrudRepository('T0008', business_columns=['id', 'name', 'location', 'is_active'])
_warehouses_svc = CrudService(_warehouses_repo)

_uoms_repo = CrudRepository('T0001', business_columns=['id', 'uom_code', 'uom_name', 'category', 'is_base_unit', 'is_active'])
_uoms_svc = CrudService(_uoms_repo)

_brands_repo = CrudRepository('T0051', business_columns=['id', 'name', 'is_active'])
_brands_svc = CrudService(_brands_repo)

_stock_repo = CrudRepository('T0009', business_columns=['id', 'product_id', 'warehouse_id', 'qty', 'reserved_qty', 'reorder_level'])
_stock_svc = CrudService(_stock_repo)


def register_tools():
    register_tool(
        Tool(name="list_products", description="List all products with optional filters", input_schema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Filter by category"},
                "brand": {"type": "string", "description": "Filter by brand"},
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
                "price": {"type": "number", "description": "Selling price"},
                "cost_price": {"type": "number", "description": "Cost price"},
                "category": {"type": "string", "description": "Category name"},
                "brand": {"type": "string", "description": "Brand name"},
                "tax_rate": {"type": "number", "description": "Tax rate (default 0.05)"},
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
                "price": {"type": "number"},
                "cost_price": {"type": "number"},
                "category": {"type": "string"},
                "brand": {"type": "string"},
                "tax_rate": {"type": "number"},
                "is_active": {"type": "boolean"},
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
    register_resource(
        Resource(uri="nova://inventory/products", name="All Products", description="List of all products"),
        _list_products,
    )


def _list_products(category: str = None, brand: str = None, limit: int = 50, offset: int = 0):
    filters = {}
    if category:
        filters["category"] = category
    if brand:
        filters["brand"] = brand
    return _products_svc.list(filters=filters or None, limit=limit, offset=offset)


def _get_product(id: int):
    return _products_svc.get(id)


def _create_product(name: str, sku: str, price: float = 0, cost_price: float = 0, category: str = None, brand: str = None, tax_rate: float = 0.05):
    return _products_svc.create({
        "name": name, "sku": sku, "price": price, "cost_price": cost_price,
        "category": category, "brand": brand, "tax_rate": tax_rate,
    })


def _update_product(id: int, **kwargs):
    payload = {k: v for k, v in kwargs.items() if v is not None and k != "id"}
    return _products_svc.update(id, payload)


def _delete_product(id: int):
    return _products_svc.delete(id)


def _search_products(query: str, limit: int = 20):
    conn = get_connection()
    try:
        sql = 'SELECT * FROM "Nova".t0005 WHERE is_active = TRUE AND (name ILIKE %s OR sku ILIKE %s) ORDER BY name LIMIT %s'
        pattern = f'%{query}%'
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (pattern, pattern, limit))
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


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    server = McpServer(name="inventory-mcp", version="1.0")
    run_stdio(server)


if __name__ == "__main__":
    main()
