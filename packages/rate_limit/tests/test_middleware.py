"""Unit tests for RateLimitMiddleware, client IP extraction, and proxy header parsing."""

from unittest.mock import AsyncMock, MagicMock, patch
import ipaddress
import json
import pytest
from starlette.datastructures import Headers

from packages.rate_limit.middleware import (
    RateLimitMiddleware,
    _classify,
    parse_trusted_proxies,
    _clean_ip,
    _to_ip_address,
    is_ip_trusted,
    _extract_header,
    _extract_peer_ip,
    extract_client_ip,
    RATE_LIMITS,
)
from packages.redis.client import InMemoryRedis, get_redis_client


class TestClassification:
    def test_classify_auth(self):
        assert _classify("/api/auth/login", "POST") == "auth"
        assert _classify("/api/auth/register", "POST") == "auth"
        assert _classify("/api/auth/refresh", "GET") == "auth"

    def test_classify_ai(self):
        assert _classify("/api/ai/chat", "POST") == "ai"
        assert _classify("/api/ai/models", "GET") == "ai"

    def test_classify_read(self):
        assert _classify("/api/products", "GET") == "read"
        assert _classify("/api/orders/123", "GET") == "read"

    def test_classify_write(self):
        assert _classify("/api/products", "POST") == "write"
        assert _classify("/api/orders/123", "PUT") == "write"
        assert _classify("/api/orders/123", "PATCH") == "write"
        assert _classify("/api/orders/123", "DELETE") == "write"


class TestTrustedProxiesParsing:
    def test_default_proxies(self, monkeypatch):
        monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
        assert parse_trusted_proxies(None) == ["127.0.0.1", "::1"]

    def test_from_env_variable(self, monkeypatch):
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1, 192.168.1.0/24 , 127.0.0.1")
        assert parse_trusted_proxies(None) == ["10.0.0.1", "192.168.1.0/24", "127.0.0.1"]

    def test_from_string_argument(self):
        result = parse_trusted_proxies("10.0.0.0/8, 172.16.0.0/12")
        assert result == ["10.0.0.0/8", "172.16.0.0/12"]

    def test_from_list_argument(self):
        result = parse_trusted_proxies([" 10.0.0.1 ", "10.0.0.2", ""])
        assert result == ["10.0.0.1", "10.0.0.2"]


class TestIpCleaningAndParsing:
    def test_clean_ip_empty_or_none(self):
        assert _clean_ip("") == ""
        assert _clean_ip(None) == ""

    def test_clean_ip_whitespace_and_quotes(self):
        assert _clean_ip("  192.168.1.1  ") == "192.168.1.1"
        assert _clean_ip('"192.168.1.1"') == "192.168.1.1"
        assert _clean_ip("'192.168.1.1'") == "192.168.1.1"

    def test_clean_ip_with_port(self):
        assert _clean_ip("192.168.1.1:8080") == "192.168.1.1"
        assert _clean_ip("[2001:db8::1]:8080") == "2001:db8::1"
        assert _clean_ip("[2001:db8::1]") == "2001:db8::1"

    def test_clean_ip_ipv6_plain(self):
        assert _clean_ip("2001:db8::1") == "2001:db8::1"
        assert _clean_ip("::1") == "::1"

    def test_to_ip_address_valid(self):
        ip4 = _to_ip_address("1.2.3.4")
        assert isinstance(ip4, ipaddress.IPv4Address)
        assert str(ip4) == "1.2.3.4"

        ip6 = _to_ip_address("2001:db8::1")
        assert isinstance(ip6, ipaddress.IPv6Address)

    def test_to_ip_address_ipv4_mapped_ipv6(self):
        mapped = _to_ip_address("::ffff:192.0.2.1")
        assert isinstance(mapped, ipaddress.IPv4Address)
        assert str(mapped) == "192.0.2.1"

    def test_to_ip_address_invalid(self):
        assert _to_ip_address("not-an-ip") is None
        assert _to_ip_address("") is None


class TestIsIpTrusted:
    def test_exact_ip_match(self):
        trusted = ["127.0.0.1", "10.0.0.1", "::1"]
        assert is_ip_trusted("127.0.0.1", trusted) is True
        assert is_ip_trusted("10.0.0.1", trusted) is True
        assert is_ip_trusted("::1", trusted) is True
        assert is_ip_trusted("10.0.0.2", trusted) is False

    def test_cidr_subnet_matching(self):
        trusted = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        assert is_ip_trusted("10.1.2.3", trusted) is True
        assert is_ip_trusted("172.20.10.5", trusted) is True
        assert is_ip_trusted("192.168.100.50", trusted) is True
        assert is_ip_trusted("198.51.100.1", trusted) is False

    def test_wildcard_matching(self):
        assert is_ip_trusted("8.8.8.8", ["*"]) is True
        assert is_ip_trusted("8.8.8.8", ["all"]) is True
        assert is_ip_trusted("8.8.8.8", ["0.0.0.0/0"]) is True
        assert is_ip_trusted("2001:db8::1", ["::/0"]) is True

    def test_invalid_and_empty_inputs(self):
        assert is_ip_trusted("", ["127.0.0.1"]) is False
        assert is_ip_trusted("127.0.0.1", []) is False
        assert is_ip_trusted("not-an-ip", ["127.0.0.1"]) is False


class TestExtractClientIp:
    def test_direct_untrusted_client_ignores_spoofed_headers(self):
        """Untrusted direct client IP cannot spoof X-Forwarded-For or X-Real-IP."""
        request = MagicMock()
        request.client.host = "198.51.100.50"
        request.headers = Headers({"x-forwarded-for": "8.8.8.8", "x-real-ip": "1.1.1.1"})

        ip = extract_client_ip(request, trusted_proxies=["127.0.0.1", "10.0.0.0/8"])
        assert ip == "198.51.100.50"

    def test_trusted_proxy_single_xff(self):
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = Headers({"x-forwarded-for": "203.0.113.195"})

        ip = extract_client_ip(request, trusted_proxies=["127.0.0.1"])
        assert ip == "203.0.113.195"

    def test_trusted_proxy_chained_xff_right_to_left(self):
        """XFF chain: Client -> Untrusted Proxy -> Trusted Proxy 2 -> Trusted Proxy 1 -> Server"""
        request = MagicMock()
        request.client.host = "10.0.0.1"
        # 198.51.100.1 is client, 203.0.113.50 is untrusted intermediate, 10.0.0.2 is trusted internal
        request.headers = Headers({
            "x-forwarded-for": "198.51.100.1, 203.0.113.50, 10.0.0.2"
        })

        # Trusted: 10.0.0.0/8
        ip = extract_client_ip(request, trusted_proxies=["10.0.0.0/8"])
        # Rightmost untrusted IP is 203.0.113.50
        assert ip == "203.0.113.50"

    def test_trusted_proxy_all_trusted_in_chain_returns_leftmost(self):
        request = MagicMock()
        request.client.host = "10.0.0.1"
        request.headers = Headers({
            "x-forwarded-for": "10.0.0.3, 10.0.0.2"
        })

        ip = extract_client_ip(request, trusted_proxies=["10.0.0.0/8"])
        assert ip == "10.0.0.3"

    def test_trusted_proxy_x_real_ip_fallback(self):
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = Headers({"x-real-ip": "203.0.113.99"})

        ip = extract_client_ip(request, trusted_proxies=["127.0.0.1"])
        assert ip == "203.0.113.99"

    def test_trusted_proxy_no_headers_returns_peer_ip(self):
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = Headers({})

        ip = extract_client_ip(request, trusted_proxies=["127.0.0.1"])
        assert ip == "127.0.0.1"

    def test_peer_ip_from_asgi_scope(self):
        request = MagicMock(spec=["scope"])
        request.scope = {
            "client": ("192.168.1.10", 54321),
            "headers": [(b"x-forwarded-for", b"203.0.113.77")],
        }

        ip = extract_client_ip(request, trusted_proxies=["192.168.0.0/16"])
        assert ip == "203.0.113.77"

    def test_trusted_proxy_ipv6_bracketed_xff(self):
        request = MagicMock()
        request.client.host = "::1"
        request.headers = Headers({"x-forwarded-for": "[2001:db8::33]:8080"})

        ip = extract_client_ip(request, trusted_proxies=["::1"])
        assert ip == "2001:db8::33"

    def test_trusted_proxy_multiple_untrusted_returns_rightmost_untrusted(self):
        """When multiple untrusted proxies exist before entering the trusted network,
        the rightmost untrusted IP is the one that contacted our edge proxy."""
        request = MagicMock()
        request.client.host = "10.0.0.1"
        # 1.1.1.1 -> 2.2.2.2 -> 3.3.3.3 -> 10.0.0.1 (trusted)
        request.headers = Headers({"x-forwarded-for": "1.1.1.1, 2.2.2.2, 3.3.3.3"})

        ip = extract_client_ip(request, trusted_proxies=["10.0.0.0/8"])
        assert ip == "3.3.3.3"


class TestRateLimitMiddleware:
    def setup_method(self):
        # Reset default limits before each test
        RATE_LIMITS["auth"] = (10, 1)
        RATE_LIMITS["read"] = (100, 1)
        RATE_LIMITS["ai"] = (10, 1)
        RATE_LIMITS["write"] = (50, 1)
        client = get_redis_client()
        try:
            client.flushdb()
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_allows_request_under_limit(self):
        app = AsyncMock()
        middleware = RateLimitMiddleware(app)
        request = MagicMock()
        request.client.host = "1.2.3.4"
        request.url.path = "/api/health"
        request.method = "GET"
        request.headers = Headers({})
        call_next = AsyncMock()
        call_next.return_value = MagicMock(status_code=200)

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_blocks_request_over_limit(self):
        app = AsyncMock()
        middleware = RateLimitMiddleware(app)
        RATE_LIMITS["read"] = (2, 1)
        request = MagicMock()
        request.client.host = "5.6.7.8"
        request.url.path = "/api/products"
        request.method = "GET"
        request.headers = Headers({})
        call_next = AsyncMock()
        call_next.return_value = MagicMock(status_code=200)

        await middleware.dispatch(request, call_next)
        await middleware.dispatch(request, call_next)
        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 429
        assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_returns_json_response_on_rate_limit(self):
        app = AsyncMock()
        middleware = RateLimitMiddleware(app)
        RATE_LIMITS["read"] = (1, 1)
        request = MagicMock()
        request.client.host = "9.9.9.9"
        request.url.path = "/api/items"
        request.method = "GET"
        request.headers = Headers({})
        call_next = AsyncMock()
        call_next.return_value = MagicMock(status_code=200)

        await middleware.dispatch(request, call_next)
        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 429
        body = json.loads(response.body)
        assert "detail" in body
        assert body["detail"] == "Rate limit exceeded. Try again later."

    @pytest.mark.asyncio
    async def test_different_ips_independent_limits(self):
        app = AsyncMock()
        middleware = RateLimitMiddleware(app)
        RATE_LIMITS["read"] = (1, 1)
        call_next = AsyncMock()
        call_next.return_value = MagicMock(status_code=200)

        req1 = MagicMock()
        req1.client.host = "10.0.0.1"
        req1.url.path = "/api/items"
        req1.method = "GET"
        req1.headers = Headers({})

        req2 = MagicMock()
        req2.client.host = "10.0.0.2"
        req2.url.path = "/api/items"
        req2.method = "GET"
        req2.headers = Headers({})

        resp1 = await middleware.dispatch(req1, call_next)
        resp2 = await middleware.dispatch(req2, call_next)
        assert resp1.status_code == 200
        assert resp2.status_code == 200

    @pytest.mark.asyncio
    async def test_different_categories_independent_limits_on_same_ip(self):
        """Rate limiting auth should not block read or write endpoints for the same client IP."""
        app = AsyncMock()
        middleware = RateLimitMiddleware(app)
        RATE_LIMITS["auth"] = (1, 1)
        RATE_LIMITS["read"] = (5, 1)
        RATE_LIMITS["write"] = (5, 1)
        call_next = AsyncMock()
        call_next.return_value = MagicMock(status_code=200)

        # Auth request 1 succeeds, request 2 gets rate limited (429)
        auth_req = MagicMock()
        auth_req.client.host = "172.20.0.15"
        auth_req.url.path = "/api/auth/login"
        auth_req.method = "POST"
        auth_req.headers = Headers({})

        resp_auth1 = await middleware.dispatch(auth_req, call_next)
        assert resp_auth1.status_code == 200

        resp_auth2 = await middleware.dispatch(auth_req, call_next)
        assert resp_auth2.status_code == 429

        # Read and write requests from the same IP still succeed
        read_req = MagicMock()
        read_req.client.host = "172.20.0.15"
        read_req.url.path = "/api/products"
        read_req.method = "GET"
        read_req.headers = Headers({})

        resp_read = await middleware.dispatch(read_req, call_next)
        assert resp_read.status_code == 200

        write_req = MagicMock()
        write_req.client.host = "172.20.0.15"
        write_req.url.path = "/api/products"
        write_req.method = "POST"
        write_req.headers = Headers({})

        resp_write = await middleware.dispatch(write_req, call_next)
        assert resp_write.status_code == 200

    @pytest.mark.asyncio
    async def test_custom_redis_client_injection(self):
        """RateLimitMiddleware can receive an explicit redis_client instance."""
        custom_redis = InMemoryRedis()
        app = AsyncMock()
        middleware = RateLimitMiddleware(app, redis_client=custom_redis)
        assert middleware._get_redis() is custom_redis

        RATE_LIMITS["read"] = (1, 1)
        req = MagicMock()
        req.client.host = "88.99.100.101"
        req.url.path = "/api/info"
        req.method = "GET"
        req.headers = Headers({})
        call_next = AsyncMock()
        call_next.return_value = MagicMock(status_code=200)

        resp1 = await middleware.dispatch(req, call_next)
        assert resp1.status_code == 200

        # Verify key was written to custom_redis
        assert len(custom_redis._zsets) == 1

    @pytest.mark.asyncio
    async def test_fallback_to_memory_when_redis_fails(self):
        """When Redis raises an unexpected exception, middleware falls back to memory smoothly."""
        app = AsyncMock()
        middleware = RateLimitMiddleware(app)
        RATE_LIMITS["write"] = (2, 1)

        request = MagicMock()
        request.client.host = "192.168.1.55"
        request.url.path = "/api/products"
        request.method = "POST"
        request.headers = Headers({})
        call_next = AsyncMock()
        call_next.return_value = MagicMock(status_code=201)

        # Mock Redis check to fail
        with patch.object(middleware, "_check_rate_limit_redis", side_effect=RuntimeError("Redis connection dropped")):
            resp1 = await middleware.dispatch(request, call_next)
            assert resp1.status_code == 201

            resp2 = await middleware.dispatch(request, call_next)
            assert resp2.status_code == 201

            resp3 = await middleware.dispatch(request, call_next)
            assert resp3.status_code == 429
            assert "Retry-After" in resp3.headers
