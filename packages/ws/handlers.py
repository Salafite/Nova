from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from packages.ws.manager import inventory_manager, order_manager

router = APIRouter()


@router.websocket('/ws/inventory/{business_id}')
async def inventory_ws(ws: WebSocket, business_id: int):
    room = f'inventory:{business_id}'
    await inventory_manager.connect(room, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        inventory_manager.disconnect(room, ws)


@router.websocket('/ws/orders/{business_id}')
async def orders_ws(ws: WebSocket, business_id: int):
    room = f'orders:{business_id}'
    await order_manager.connect(room, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        order_manager.disconnect(room, ws)
