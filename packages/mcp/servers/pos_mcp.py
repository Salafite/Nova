from packages.mcp.registry import register_tool
from packages.mcp.types import Tool
from modules.pos.models.pos import PosCheckoutRequest, PosCartItem, PosPaymentSplit
from modules.pos.controllers.checkout import process_pos_checkout
from packages.database.connection import get_connection, release_connection
import psycopg2.extras
from modules.core.context import get_current_tenant


def _pos_checkout_handler(cart_items, customer_id=None, customer_name="Walk-in Customer", warehouse_id=1, payment_method="Cash", payments=None, amount_tendered=None, notes=None):
    items = []
    for item in cart_items:
        if isinstance(item, dict):
            items.append(PosCartItem(**item))
        elif isinstance(item, PosCartItem):
            items.append(item)
            
    payment_splits = []
    if payments:
        for p in payments:
            if isinstance(p, dict):
                payment_splits.append(PosPaymentSplit(**p))
            else:
                payment_splits.append(p)

    req = PosCheckoutRequest(
        cart_items=items,
        customer_id=customer_id,
        customer_name=customer_name or "Walk-in Customer",
        warehouse_id=warehouse_id if warehouse_id is not None else 1,
        payment_method=payment_method or "Cash",
        payments=payment_splits if payment_splits else None,
        amount_tendered=amount_tendered,
        notes=notes
    )
    res = process_pos_checkout(req)
    return res.model_dump()


def _pos_customer_lookup_handler(query: str, limit: int = 10):
    tenant_id = get_current_tenant()
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if tenant_id is not None:
            cur.execute(
                'SELECT id, name, phone, email, customer_group, credit_limit, current_balance FROM "Nova".t0010 WHERE (name ILIKE %s OR phone ILIKE %s) AND business_id = %s LIMIT %s',
                (f"%{query}%", f"%{query}%", tenant_id, limit)
            )
        else:
            cur.execute(
                'SELECT id, name, phone, email, customer_group, credit_limit, current_balance FROM "Nova".t0010 WHERE name ILIKE %s OR phone ILIKE %s LIMIT %s',
                (f"%{query}%", f"%{query}%", limit)
            )
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        release_connection(conn)


def register_tools():
    register_tool(
        Tool(
            name="pos_checkout",
            description="Process POS checkout by creating sales order and adjusting stock",
            input_schema={
                "type": "object",
                "properties": {
                    "cart_items": {
                        "type": "array",
                        "description": "List of cart items with product_id, product_name, qty, unit_price",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_id": {"type": "integer"},
                                "product_name": {"type": "string"},
                                "qty": {"type": "number"},
                                "unit_price": {"type": "number"},
                            },
                            "required": ["product_id", "product_name", "qty", "unit_price"],
                        },
                    },
                    "customer_id": {"type": "integer", "description": "Optional Customer ID"},
                    "customer_name": {"type": "string", "description": "Customer name (default: Walk-in Customer)"},
                    "warehouse_id": {"type": "integer", "description": "Warehouse ID (default: 1)"},
                    "payment_method": {"type": "string", "description": "Payment method (default: Cash)"},
                    "payments": {
                        "type": "array",
                        "description": "Optional list of split payments",
                        "items": {
                            "type": "object",
                            "properties": {
                                "payment_method": {"type": "string"},
                                "amount": {"type": "number"},
                                "reference": {"type": "string"}
                            },
                            "required": ["payment_method", "amount"]
                        }
                    },
                    "amount_tendered": {"type": "number", "description": "Total cash/tendered amount"},
                    "notes": {"type": "string", "description": "Optional notes"},
                },
                "required": ["cart_items"],
            },
        ),
        _pos_checkout_handler,
    )

    register_tool(
        Tool(
            name="pos_customer_lookup",
            description="Lookup POS customers by name or phone",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query for name or phone"},
                    "limit": {"type": "integer", "description": "Max results (default: 10)"},
                },
                "required": ["query"],
            },
        ),
        _pos_customer_lookup_handler,
    )


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    server = McpServer(name="pos-mcp", version="1.0")
    run_stdio(server)


if __name__ == "__main__":
    main()
