from packages.mcp.registry import register_tool
from packages.mcp.types import Tool
from modules.pos.models.pos import PosCheckoutRequest, PosCartItem
from modules.pos.controllers.checkout import process_pos_checkout


def _pos_checkout_handler(cart_items, customer_name="Walk-in Customer", warehouse_id=1, payment_method="Cash", notes=None):
    items = []
    for item in cart_items:
        if isinstance(item, dict):
            items.append(PosCartItem(**item))
        elif isinstance(item, PosCartItem):
            items.append(item)

    req = PosCheckoutRequest(
        cart_items=items,
        customer_name=customer_name or "Walk-in Customer",
        warehouse_id=warehouse_id if warehouse_id is not None else 1,
        payment_method=payment_method or "Cash",
        notes=notes
    )
    res = process_pos_checkout(req)
    return res.model_dump()


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
                    "customer_name": {"type": "string", "description": "Customer name (default: Walk-in Customer)"},
                    "warehouse_id": {"type": "integer", "description": "Warehouse ID (default: 1)"},
                    "payment_method": {"type": "string", "description": "Payment method (default: Cash)"},
                    "notes": {"type": "string", "description": "Optional notes"},
                },
                "required": ["cart_items"],
            },
        ),
        _pos_checkout_handler,
    )


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    server = McpServer(name="pos-mcp", version="1.0")
    run_stdio(server)


if __name__ == "__main__":
    main()
