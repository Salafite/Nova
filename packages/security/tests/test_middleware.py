from unittest.mock import AsyncMock, MagicMock
import pytest
from packages.security.middleware import SecurityHeadersMiddleware


@pytest.mark.asyncio
async def test_sets_security_headers():
    middleware = SecurityHeadersMiddleware(AsyncMock())
    request = MagicMock()
    response = MagicMock(status_code=200)
    response.headers = {}
    call_next = AsyncMock(return_value=response)

    await middleware.dispatch(request, call_next)

    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['X-XSS-Protection'] == '1; mode=block'
    assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    assert response.headers['Permissions-Policy'] == 'camera=(), microphone=(), geolocation=()'


@pytest.mark.asyncio
async def test_sets_csp_default():
    middleware = SecurityHeadersMiddleware(AsyncMock())
    request = MagicMock()
    response = MagicMock(status_code=200)
    response.headers = {}
    call_next = AsyncMock(return_value=response)

    await middleware.dispatch(request, call_next)

    csp = response.headers['Content-Security-Policy']
    assert "default-src 'self'" in csp
    assert "script-src 'self' 'unsafe-inline'" in csp
    assert "style-src 'self' 'unsafe-inline'" in csp
    assert 'connect-src' in csp
    assert 'font-src' in csp
    assert 'img-src' in csp


@pytest.mark.asyncio
async def test_does_not_overwrite_existing_csp():
    middleware = SecurityHeadersMiddleware(AsyncMock())
    request = MagicMock()
    response = MagicMock(status_code=200)
    response.headers = {'Content-Security-Policy': 'default-src example.com'}
    call_next = AsyncMock(return_value=response)

    await middleware.dispatch(request, call_next)

    assert response.headers['Content-Security-Policy'] == 'default-src example.com'


@pytest.mark.asyncio
async def test_sets_headers_on_all_status_codes():
    middleware = SecurityHeadersMiddleware(AsyncMock())
    request = MagicMock()
    response = MagicMock(status_code=404)
    response.headers = {}
    call_next = AsyncMock(return_value=response)

    await middleware.dispatch(request, call_next)

    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
