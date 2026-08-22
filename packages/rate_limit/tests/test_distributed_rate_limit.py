"""Tests for distributed rate limiting with Redis backend and proxy header support.

Validates sliding window counters, multi-worker process state sharing,
proxy header client extraction (single & chained proxies), Retry-After headers,
and independent IP / category isolation.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest

from packages.rate_limit.middleware import (
    RateLimitMiddleware,
    RATE_LIMITS,
    RATE_LIMIT_KEY_PREFIX,
    extract_client_ip,
)
from packages.redis.client import InMemoryRedis, get_redis_client


class TestDistributedSlidingWindowRateLimiting:
    def setup_method(self):
        # Reset default limits
        RATE_LIMITS["auth"] = (10, 1)
        RATE_LIMITS["read"] = (100, 1)
        RATE_LIMITS["ai"] = (10, 1)
        RATE_LIMITS["write"] = (50, 1)
        self.redis = InMemoryRedis()

    @pytest.mark.asyncio
    async def test_shared_state_across_four_worker_processes(self):
        """Simulate 4 independent uvicorn worker processes sharing the same Redis instance.
        Requests handled round-robin across workers must contribute to the same distributed limit.
        """
        RATE_LIMITS["read"] = (4, 1)  # 4 requests per 1 second

        workers = [
            RateLimitMiddleware(AsyncMock(), redis_client=self.redis)
            for _ in range(4)
        ]

        call_next = AsyncMock()
        call_next.return_value = MagicMock(status_code=200)

        client_ip = "198.51.100.44"

        # Worker 0, Worker 1, Worker 2, Worker 3 each process 1 request (total: 4)
        for i in range(4):
            req = MagicMock()
            req.client.host = client_ip
            req.url.path = "/api/products"
            req.method = "GET"
            req.headers = {}
            resp = await workers[i].dispatch(req, call_next)
            assert resp.status_code == 200, f"Worker {i} failed to allow request {i+1}"

        # Request 5 handled by Worker 0 should be blocked (429)
        req_blocked = MagicMock()
        req_blocked.client.host = client_ip
        req_blocked.url.path = "/api/products"
        req_blocked.method = "GET"
        req_blocked.headers = {}

        resp_blocked = await workers[0].dispatch(req_blocked, call_next)
        assert resp_blocked.status_code == 429
        assert "Retry-After" in resp_blocked.headers
        body = json.loads(resp_blocked.body)
        assert body["detail"] == "Rate limit exceeded. Try again later."

    @pytest.mark.asyncio
    async def test_sliding_window_roll_off_and_recovery(self):
        """Requests from a previous time window roll off as time advances."""
        RATE_LIMITS["read"] = (2, 1)  # 2 requests per 1 second

        middleware = RateLimitMiddleware(AsyncMock(), redis_client=self.redis)
        call_next = AsyncMock()
        call_next.return_value = MagicMock(status_code=200)

        client_ip = "192.0.2.77"
        t0 = 1000.0

        # Send 2 requests at t0
        allowed1, _ = middleware._check_rate_limit_redis(client_ip, "read", 2, 1.0, t0)
        allowed2, _ = middleware._check_rate_limit_redis(client_ip, "read", 2, 1.0, t0 + 0.1)
        assert allowed1 is True
        assert allowed2 is True

        # 3rd request at t0 + 0.2 should be blocked
        allowed3, retry_after = middleware._check_rate_limit_redis(client_ip, "read", 2, 1.0, t0 + 0.2)
        assert allowed3 is False
        assert retry_after >= 1

        # At t0 + 1.05, the first request (at t0) has rolled off (now - window = 1000.05 > 1000.0)
        # So 1 new request should be allowed
        allowed4, _ = middleware._check_rate_limit_redis(client_ip, "read", 2, 1.0, t0 + 1.05)
        assert allowed4 is True

        # At t0 + 1.06, we now have request 2 (t0+0.1) and request 4 (t0+1.05), so next is blocked
        allowed5, _ = middleware._check_rate_limit_redis(client_ip, "read", 2, 1.0, t0 + 1.06)
        assert allowed5 is False

        # At t0 + 2.1, all previous requests have rolled off
        allowed6, _ = middleware._check_rate_limit_redis(client_ip, "read", 2, 1.0, t0 + 2.1)
        assert allowed6 is True

    @pytest.mark.asyncio
    async def test_redis_key_format_and_ttl_expiration(self):
        """Keys are written with prefix 'nova:ratelimit:{client_ip}:{category}' and valid TTL."""
        RATE_LIMITS["write"] = (5, 1)
        middleware = RateLimitMiddleware(AsyncMock(), redis_client=self.redis)

        client_ip = "203.0.113.88"
        category = "write"
        now = time.time()

        allowed, _ = middleware._check_rate_limit_redis(client_ip, category, 5, 1.0, now)
        assert allowed is True

        expected_key = f"{RATE_LIMIT_KEY_PREFIX}{client_ip}:{category}"
        zcard = self.redis.zcard(expected_key)
        assert zcard == 1

        ttl = self.redis.ttl(expected_key)
        assert 0 < ttl <= 60


class TestProxyGatewayClientDifferentiation:
    """Ensure corporate proxy gateways or reverse proxies do not cause single-IP rate limit DoS."""

    def setup_method(self):
        RATE_LIMITS["read"] = (3, 1)
        self.redis = InMemoryRedis()
        self.trusted_proxies = ["127.0.0.1", "10.0.0.0/8", "172.16.0.0/12"]

    @pytest.mark.asyncio
    async def test_distinct_clients_behind_same_trusted_proxy_are_isolated(self):
        """Client A and Client B share the same internal proxy gateway (10.0.0.1).
        Client A exceeding rate limits should NOT block Client B.
        """
        app = AsyncMock()
        middleware = RateLimitMiddleware(
            app,
            trusted_proxies=self.trusted_proxies,
            redis_client=self.redis,
        )

        call_next = AsyncMock()
        call_next.return_value = MagicMock(status_code=200)

        proxy_gateway_ip = "10.0.0.1"
        client_a_ip = "198.51.100.10"
        client_b_ip = "198.51.100.20"

        # Client A makes 3 requests (limit is 3)
        for _ in range(3):
            req = MagicMock()
            req.client.host = proxy_gateway_ip
            req.url.path = "/api/products"
            req.method = "GET"
            req.headers = {"x-forwarded-for": client_a_ip}
            resp = await middleware.dispatch(req, call_next)
            assert resp.status_code == 200

        # Client A makes 4th request -> 429
        req_a4 = MagicMock()
        req_a4.client.host = proxy_gateway_ip
        req_a4.url.path = "/api/products"
        req_a4.method = "GET"
        req_a4.headers = {"x-forwarded-for": client_a_ip}
        resp_a4 = await middleware.dispatch(req_a4, call_next)
        assert resp_a4.status_code == 429

        # Client B makes requests through the same proxy -> should succeed
        for _ in range(3):
            req_b = MagicMock()
            req_b.client.host = proxy_gateway_ip
            req_b.url.path = "/api/products"
            req_b.method = "GET"
            req_b.headers = {"x-forwarded-for": client_b_ip}
            resp_b = await middleware.dispatch(req_b, call_next)
            assert resp_b.status_code == 200

    @pytest.mark.asyncio
    async def test_chained_multi_hop_proxy_resolution(self):
        """X-Forwarded-For: Client -> UntrustedEdge -> InternalProxy2 -> InternalProxy1"""
        app = AsyncMock()
        middleware = RateLimitMiddleware(
            app,
            trusted_proxies=["10.0.0.0/8", "172.16.0.0/12"],
            redis_client=self.redis,
        )

        call_next = AsyncMock()
        call_next.return_value = MagicMock(status_code=200)

        # Immediate peer is 10.0.0.1 (trusted)
        # Chain is: 192.0.2.1 (original client), 203.0.113.99 (untrusted external proxy), 172.16.0.5 (trusted proxy 2)
        req = MagicMock()
        req.client.host = "10.0.0.1"
        req.url.path = "/api/products"
        req.method = "GET"
        req.headers = {"x-forwarded-for": "192.0.2.1, 203.0.113.99, 172.16.0.5"}

        # Should extract the first untrusted IP from the right: 203.0.113.99
        extracted = extract_client_ip(req, trusted_proxies=["10.0.0.0/8", "172.16.0.0/12"])
        assert extracted == "203.0.113.99"

    @pytest.mark.asyncio
    async def test_untrusted_direct_peer_cannot_bypass_limits_with_spoofed_xff(self):
        """Untrusted direct client trying to cycle spoofed XFF headers is rate-limited on peer IP."""
        app = AsyncMock()
        middleware = RateLimitMiddleware(
            app,
            trusted_proxies=["10.0.0.0/8"],
            redis_client=self.redis,
        )
        call_next = AsyncMock()
        call_next.return_value = MagicMock(status_code=200)

        attacker_real_ip = "198.51.100.77"

        # Attacker sends 3 requests with spoofed XFF headers
        for i in range(3):
            req = MagicMock()
            req.client.host = attacker_real_ip
            req.url.path = "/api/products"
            req.method = "GET"
            req.headers = {"x-forwarded-for": f"1.2.3.{i+1}"}
            resp = await middleware.dispatch(req, call_next)
            assert resp.status_code == 200

        # 4th request with yet another fake IP is blocked based on real peer IP
        req4 = MagicMock()
        req4.client.host = attacker_real_ip
        req4.url.path = "/api/products"
        req4.method = "GET"
        req4.headers = {"x-forwarded-for": "9.9.9.9"}
        resp4 = await middleware.dispatch(req4, call_next)
        assert resp4.status_code == 429


class TestFastApiAppIntegration:
    """Integration test suite mounting RateLimitMiddleware on a real FastAPI application."""

    def setup_method(self):
        self.redis = InMemoryRedis()
        RATE_LIMITS["auth"] = (2, 1)
        RATE_LIMITS["read"] = (3, 1)
        RATE_LIMITS["write"] = (2, 1)
        RATE_LIMITS["ai"] = (2, 1)

        self.app = FastAPI()
        self.app.add_middleware(
            RateLimitMiddleware,
            trusted_proxies=["127.0.0.1", "10.0.0.0/8"],
            redis_client=self.redis,
        )

        @self.app.post("/api/auth/login")
        def login():
            return {"token": "jwt-token-123"}

        @self.app.get("/api/products")
        def list_products():
            return [{"id": 1, "name": "Item A"}]

        @self.app.post("/api/orders")
        def create_order():
            return {"order_id": "ord-1"}

        @self.app.post("/api/ai/chat")
        def ai_chat():
            return {"response": "hello"}

        self.client = TestClient(self.app)

    def test_http_rate_limit_exceeded_returns_429_with_headers(self):
        headers = {"X-Forwarded-For": "203.0.113.5"}

        # 2 auth requests allowed
        resp1 = self.client.post("/api/auth/login", headers=headers)
        assert resp1.status_code == 200

        resp2 = self.client.post("/api/auth/login", headers=headers)
        assert resp2.status_code == 200

        # 3rd request blocked
        resp3 = self.client.post("/api/auth/login", headers=headers)
        assert resp3.status_code == 429
        assert resp3.headers["Retry-After"] == "1"
        data = resp3.json()
        assert data["detail"] == "Rate limit exceeded. Try again later."

    def test_independent_route_categories_on_same_client(self):
        headers = {"X-Forwarded-For": "203.0.113.6"}

        # Exceed auth limit (2 requests)
        self.client.post("/api/auth/login", headers=headers)
        self.client.post("/api/auth/login", headers=headers)
        resp_auth = self.client.post("/api/auth/login", headers=headers)
        assert resp_auth.status_code == 429

        # Read endpoints should still work (limit is 3)
        resp_read1 = self.client.get("/api/products", headers=headers)
        assert resp_read1.status_code == 200
        resp_read2 = self.client.get("/api/products", headers=headers)
        assert resp_read2.status_code == 200

        # AI endpoints should also work independently
        resp_ai = self.client.post("/api/ai/chat", headers=headers)
        assert resp_ai.status_code == 200

        # Write endpoints should also work independently
        resp_write = self.client.post("/api/orders", headers=headers)
        assert resp_write.status_code == 200


class TestConcurrentWorkerExecution:
    @pytest.mark.asyncio
    async def test_concurrent_sliding_window_requests_enforce_exact_limit(self):
        """Simulate concurrent requests from parallel workers hitting the same client IP."""
        redis = InMemoryRedis()
        RATE_LIMITS["read"] = (10, 1)  # limit: 10 per second

        workers = [RateLimitMiddleware(AsyncMock(), redis_client=redis) for _ in range(4)]
        client_ip = "192.0.2.111"

        async def make_request(worker_idx: int, req_id: int):
            req = MagicMock()
            req.client.host = client_ip
            req.url.path = "/api/products"
            req.method = "GET"
            req.headers = {}
            call_next = AsyncMock(return_value=MagicMock(status_code=200))
            return await workers[worker_idx % 4].dispatch(req, call_next)

        # Run 25 concurrent requests
        tasks = [make_request(i, i) for i in range(25)]
        responses = await asyncio.gather(*tasks)

        status_codes = [r.status_code for r in responses]
        successes = status_codes.count(200)
        blocked = status_codes.count(429)

        assert successes == 10
        assert blocked == 15
