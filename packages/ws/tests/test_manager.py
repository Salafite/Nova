import json
from unittest.mock import AsyncMock
import pytest
from packages.ws.manager import ConnectionManager


@pytest.mark.asyncio
async def test_connect_adds_to_room():
    manager = ConnectionManager()
    ws = AsyncMock()
    await manager.connect('room1', ws)
    assert ws in manager._rooms['room1']
    ws.accept.assert_awaited_once()


@pytest.mark.asyncio
async def test_disconnect_removes_from_room():
    manager = ConnectionManager()
    ws = AsyncMock()
    await manager.connect('room1', ws)
    manager.disconnect('room1', ws)
    assert 'room1' not in manager._rooms


@pytest.mark.asyncio
async def test_disconnect_does_not_remove_other_connections():
    manager = ConnectionManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    await manager.connect('room1', ws1)
    await manager.connect('room1', ws2)
    manager.disconnect('room1', ws1)
    assert 'room1' in manager._rooms
    assert ws2 in manager._rooms['room1']


@pytest.mark.asyncio
async def test_broadcast_sends_to_all_in_room():
    manager = ConnectionManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    await manager.connect('room1', ws1)
    await manager.connect('room1', ws2)

    await manager.broadcast('room1', 'test_event', {'key': 'value'})

    expected = json.dumps({'event': 'test_event', 'data': {'key': 'value'}})
    ws1.send_text.assert_awaited_once_with(expected)
    ws2.send_text.assert_awaited_once_with(expected)


@pytest.mark.asyncio
async def test_broadcast_removes_stale_connections():
    manager = ConnectionManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    ws2.send_text.side_effect = Exception('gone')
    await manager.connect('room1', ws1)
    await manager.connect('room1', ws2)

    await manager.broadcast('room1', 'evt', {})

    assert ws2 not in manager._rooms.get('room1', set())


@pytest.mark.asyncio
async def test_broadcast_empty_room_does_not_error():
    manager = ConnectionManager()
    await manager.broadcast('nonexistent', 'evt', {})


def test_inventory_and_order_managers_are_singletons():
    from packages.ws.manager import inventory_manager, order_manager
    assert inventory_manager is not None
    assert order_manager is not None
    assert inventory_manager is not order_manager


@pytest.mark.asyncio
async def test_multiple_rooms_are_independent():
    manager = ConnectionManager()
    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await manager.connect('room_a', ws_a)
    await manager.connect('room_b', ws_b)

    await manager.broadcast('room_a', 'evt', {})

    ws_a.send_text.assert_awaited()
    ws_b.send_text.assert_not_awaited()
