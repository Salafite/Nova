from unittest.mock import AsyncMock, MagicMock
import pytest
from packages.cache.middleware import CacheControlMiddleware


@pytest.mark.asyncio
async def test_get_api_returns_private_max_age():
    middleware = CacheControlMiddleware(AsyncMock())
    request = MagicMock()
    request.method = 'GET'
    request.url.path = '/api/products'
    response = MagicMock(status_code=200)
    response.headers = {}
    call_next = AsyncMock(return_value=response)

    await middleware.dispatch(request, call_next)

    assert response.headers['Cache-Control'] == 'private, max-age=30'


@pytest.mark.asyncio
async def test_health_endpoint_no_cache():
    middleware = CacheControlMiddleware(AsyncMock())
    request = MagicMock()
    request.method = 'GET'
    request.url.path = '/api/v1/health'
    response = MagicMock(status_code=200)
    response.headers = {}
    call_next = AsyncMock(return_value=response)

    await middleware.dispatch(request, call_next)

    assert response.headers['Cache-Control'] == 'no-cache'


@pytest.mark.asyncio
async def test_static_assets_immutable():
    middleware = CacheControlMiddleware(AsyncMock())
    request = MagicMock()
    request.method = 'GET'
    request.url.path = '/assets/app-DEADBEEF.js'
    response = MagicMock(status_code=200)
    response.headers = {}
    call_next = AsyncMock(return_value=response)

    await middleware.dispatch(request, call_next)

    assert response.headers['Cache-Control'] == 'public, max-age=31536000, immutable'


@pytest.mark.asyncio
async def test_icons_immutable():
    middleware = CacheControlMiddleware(AsyncMock())
    request = MagicMock()
    request.method = 'GET'
    request.url.path = '/icons/icon-192.png'
    response = MagicMock(status_code=200)
    response.headers = {}
    call_next = AsyncMock(return_value=response)

    await middleware.dispatch(request, call_next)

    assert response.headers['Cache-Control'] == 'public, max-age=31536000, immutable'


@pytest.mark.asyncio
async def test_manifest_immutable():
    middleware = CacheControlMiddleware(AsyncMock())
    request = MagicMock()
    request.method = 'GET'
    request.url.path = '/manifest.json'
    response = MagicMock(status_code=200)
    response.headers = {}
    call_next = AsyncMock(return_value=response)

    await middleware.dispatch(request, call_next)

    assert response.headers['Cache-Control'] == 'public, max-age=31536000, immutable'


@pytest.mark.asyncio
async def test_non_get_no_header():
    middleware = CacheControlMiddleware(AsyncMock())
    request = MagicMock()
    request.method = 'POST'
    request.url.path = '/api/products'
    response = MagicMock(status_code=200)
    response.headers = {}
    call_next = AsyncMock(return_value=response)

    await middleware.dispatch(request, call_next)

    assert 'Cache-Control' not in response.headers


@pytest.mark.asyncio
async def test_non_api_path_no_header():
    middleware = CacheControlMiddleware(AsyncMock())
    request = MagicMock()
    request.method = 'GET'
    request.url.path = '/docs'
    response = MagicMock(status_code=200)
    response.headers = {}
    call_next = AsyncMock(return_value=response)

    await middleware.dispatch(request, call_next)

    assert 'Cache-Control' not in response.headers
