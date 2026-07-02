import time
from unittest.mock import AsyncMock, MagicMock
import pytest
from packages.rate_limit.middleware import RateLimitMiddleware, _classify, RATE_LIMITS


def test_classify_auth():
    assert _classify('/api/auth/', 'POST') == 'auth'


def test_classify_read():
    assert _classify('/api/products', 'GET') == 'read'


def test_classify_write():
    assert _classify('/api/products', 'POST') == 'write'


@pytest.mark.asyncio
async def test_allows_request_under_limit():
    app = AsyncMock()
    app.side_effect = lambda req: AsyncMock()
    middleware = RateLimitMiddleware(app)
    request = MagicMock()
    request.client.host = '1.2.3.4'
    request.url.path = '/api/health'
    request.method = 'GET'
    call_next = AsyncMock()
    call_next.return_value = MagicMock(status_code=200)

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_blocks_request_over_limit():
    app = AsyncMock()
    middleware = RateLimitMiddleware(app)
    RATE_LIMITS['read'] = (2, 1)
    request = MagicMock()
    request.client.host = '5.6.7.8'
    request.url.path = '/api/products'
    request.method = 'GET'
    call_next = AsyncMock()
    call_next.return_value = MagicMock(status_code=200)

    await middleware.dispatch(request, call_next)
    await middleware.dispatch(request, call_next)
    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 429
    assert 'Retry-After' in response.headers


@pytest.mark.asyncio
async def test_returns_json_response_on_rate_limit():
    app = AsyncMock()
    middleware = RateLimitMiddleware(app)
    RATE_LIMITS['read'] = (1, 1)
    request = MagicMock()
    request.client.host = '9.9.9.9'
    request.url.path = '/api/items'
    request.method = 'GET'
    call_next = AsyncMock()
    call_next.return_value = MagicMock(status_code=200)

    await middleware.dispatch(request, call_next)
    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 429
    import json
    body = json.loads(response.body)
    assert 'detail' in body


@pytest.mark.asyncio
async def test_different_ips_independent_limits():
    app = AsyncMock()
    middleware = RateLimitMiddleware(app)
    RATE_LIMITS['read'] = (1, 1)
    call_next = AsyncMock()
    call_next.return_value = MagicMock(status_code=200)

    req1 = MagicMock()
    req1.client.host = '10.0.0.1'
    req1.url.path = '/api/items'
    req1.method = 'GET'

    req2 = MagicMock()
    req2.client.host = '10.0.0.2'
    req2.url.path = '/api/items'
    req2.method = 'GET'

    resp1 = await middleware.dispatch(req1, call_next)
    resp2 = await middleware.dispatch(req2, call_next)
    assert resp1.status_code == 200
    assert resp2.status_code == 200
