"""Multi-worker simulation integration test suite.

Simulates 4 concurrent Uvicorn worker processes sharing a Redis instance to validate:
1. 100% Tier 2 MCP action confirmation success across worker boundaries (Worker A -> Worker B)
2. Atomic single-execution guarantee under concurrent confirmation races
3. Cross-worker context preservation
4. Distributed sliding window rate limiting and proxy IP throttling across all 4 workers
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock
import pytest

from packages.mcp.registry import (
    register_tool,
    call_tool,
    propose_action,
    confirm_action,
    get_current_user,
    _tools,
    _pending_actions,
    _current_user,
)
from packages.mcp.types import Tool
from packages.rate_limit.middleware import (
    RateLimitMiddleware,
    RATE_LIMITS,
    extract_client_ip,
)
from packages.redis.client import InMemoryRedis, get_redis_client


class SimulatedWorkerProcess:
    """Simulates an isolated Uvicorn worker process that has its own local memory
    but shares the global Redis instance with other worker processes.
    """

    def __init__(self, worker_id: int, redis_client: InMemoryRedis, trusted_proxies: list[str] | None = None):
        self.worker_id = worker_id
        self.redis = redis_client
        self.trusted_proxies = trusted_proxies or ["127.0.0.1", "10.0.0.0/8", "172.16.0.0/12"]
        self.local_memory_actions: dict = {}
        self.middleware = RateLimitMiddleware(
            AsyncMock(),
            trusted_proxies=self.trusted_proxies,
            redis_client=self.redis,
        )

    def propose(self, tool_name: str, arguments: dict, user_context: dict | None = None) -> dict:
        # Simulate worker local memory isolation
        _pending_actions.clear()
        token = None
        if user_context is not None:
            token = _current_user.set(user_context)
        try:
            return propose_action(tool_name, arguments)
        finally:
            if token is not None:
                _current_user.reset(token)
            # Ensure in-memory process dict is cleared on other workers
            _pending_actions.clear()

    def confirm(self, action_id: str) -> any:
        # Clear in-memory process dict to guarantee resolution comes from Redis
        _pending_actions.clear()
        return confirm_action(action_id)

    async def handle_http_request(self, path: str, method: str, client_ip: str, headers: dict | None = None) -> any:
        req = MagicMock()
        req.client.host = client_ip
        req.url.path = path
        req.method = method
        req.headers = headers or {}
        call_next = AsyncMock(return_value=MagicMock(status_code=200))
        return await self.middleware.dispatch(req, call_next)


class TestMultiWorkerSimulation:
    def setup_method(self):
        _tools.clear()
        _pending_actions.clear()
        self.redis = InMemoryRedis()
        # Create 4 simulated Uvicorn workers
        self.workers = [SimulatedWorkerProcess(i, self.redis) for i in range(4)]

        # Register standard Tier 2 tools across workers
        self._register_tier2_tools()

    def _register_tier2_tools(self):
        register_tool(
            Tool(name="delete_product", description="Delete product", input_schema={}, tier="tier2"),
            lambda id: {"status": "deleted", "product_id": id},
        )
        register_tool(
            Tool(name="confirm_order", description="Confirm sales order", input_schema={}, tier="tier2"),
            lambda id: {"status": "confirmed", "order_id": id},
        )
        register_tool(
            Tool(name="cancel_order", description="Cancel sales order", input_schema={}, tier="tier2"),
            lambda id: {"status": "cancelled", "order_id": id},
        )
        register_tool(
            Tool(name="convert_quotation_to_order", description="Convert quote", input_schema={}, tier="tier2"),
            lambda id: {"status": "converted", "quote_id": id, "order_id": f"ORD-{id}"},
        )
        register_tool(
            Tool(name="mark_all_notifications_read", description="Mark all read", input_schema={}, tier="tier2"),
            lambda user_id: {"status": "all_read", "user_id": user_id, "updated": 5},
        )

    def test_tier2_propose_on_worker_0_confirm_on_worker_3(self):
        """Worker 0 proposes order confirmation; Worker 3 confirms it."""
        proposal = self.workers[0].propose("confirm_order", {"id": 1001})
        action_id = proposal["action_id"]

        result = self.workers[3].confirm(action_id)
        assert result == {"status": "confirmed", "order_id": 1001}

    def test_all_worker_pairwise_confirmation_matrix(self):
        """Test all 16 possible Worker (proposer) -> Worker (confirmer) combinations.
        Guarantees 100% success rate across all worker boundaries.
        """
        tools_to_test = [
            ("delete_product", {"id": 10}),
            ("confirm_order", {"id": 20}),
            ("cancel_order", {"id": 30}),
            ("convert_quotation_to_order", {"id": 40}),
            ("mark_all_notifications_read", {"user_id": 50}),
        ]

        count = 0
        for proposer_id in range(4):
            for confirmer_id in range(4):
                tool_name, args = tools_to_test[count % len(tools_to_test)]
                user = {"id": proposer_id + 1, "username": f"user_{proposer_id}", "business_id": 100}

                # Propose on proposer worker
                proposal = self.workers[proposer_id].propose(tool_name, args, user_context=user)
                action_id = proposal["action_id"]

                # Confirm on confirmer worker
                result = self.workers[confirmer_id].confirm(action_id)
                assert result is not None
                assert "status" in result

                count += 1

        assert count == 16

    def test_concurrent_confirmation_race_prevents_duplicate_execution(self):
        """Simulate a race where Worker 1, Worker 2, Worker 3 all attempt to confirm the same action concurrently.
        Exactly one worker must succeed; the other two must receive ValueError (Action not found or expired).
        """
        proposal = self.workers[0].propose("delete_product", {"id": 99})
        action_id = proposal["action_id"]

        results = []
        errors = []

        def try_confirm(worker: SimulatedWorkerProcess):
            try:
                res = worker.confirm(action_id)
                results.append(res)
            except ValueError as e:
                errors.append(str(e))

        # Run concurrent confirmations across workers 1, 2, 3 using ThreadPoolExecutor
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(try_confirm, self.workers[i]) for i in (1, 2, 3)]
            concurrent.futures.wait(futures)

        # Exactly 1 success, 2 failures
        assert len(results) == 1
        assert results[0] == {"status": "deleted", "product_id": 99}
        assert len(errors) == 2
        for err in errors:
            assert "Action not found or expired" in err

    def test_user_context_forwarded_across_worker_boundaries(self):
        """User context attached during proposal on Worker 0 is available in tool execution on Worker 2."""
        captured = []
        register_tool(
            Tool(name="custom_audit_op", description="Audit", input_schema={}, tier="tier2"),
            lambda: captured.append(get_current_user()),
        )

        user = {"id": 77, "username": "auditor_jane", "role": "admin", "business_id": 12}
        proposal = self.workers[0].propose("custom_audit_op", {}, user_context=user)
        action_id = proposal["action_id"]

        self.workers[2].confirm(action_id)

        assert len(captured) == 1
        assert captured[0] == user

    @pytest.mark.asyncio
    async def test_distributed_rate_limiting_across_all_four_workers(self):
        """Requests from a single client IP distributed across all 4 workers hit the shared rate limit."""
        RATE_LIMITS["read"] = (4, 1)  # 4 requests per second
        client_ip = "198.51.100.123"

        # Worker 0, 1, 2, 3 each process 1 request -> all 200 OK
        for i in range(4):
            resp = await self.workers[i].handle_http_request("/api/products", "GET", client_ip)
            assert resp.status_code == 200

        # Next request on Worker 1 should be rate limited (429)
        resp_blocked = await self.workers[1].handle_http_request("/api/products", "GET", client_ip)
        assert resp_blocked.status_code == 429
        assert "Retry-After" in resp_blocked.headers

    @pytest.mark.asyncio
    async def test_proxy_gateway_client_isolation_under_multi_worker_load(self):
        """Multiple client devices connecting via the same proxy gateway (10.0.0.1).
        When Client A is throttled on Worker 0, Client B on Worker 3 is not affected.
        """
        RATE_LIMITS["write"] = (2, 1)  # 2 requests per second
        gateway_ip = "10.0.0.1"

        client_a = "192.0.2.10"
        client_b = "192.0.2.20"

        # Client A sends 2 requests through Worker 0 and Worker 1
        r1 = await self.workers[0].handle_http_request("/api/orders", "POST", gateway_ip, {"x-forwarded-for": client_a})
        r2 = await self.workers[1].handle_http_request("/api/orders", "POST", gateway_ip, {"x-forwarded-for": client_a})
        assert r1.status_code == 200
        assert r2.status_code == 200

        # Client A sends 3rd request through Worker 2 -> 429
        r3 = await self.workers[2].handle_http_request("/api/orders", "POST", gateway_ip, {"x-forwarded-for": client_a})
        assert r3.status_code == 429

        # Client B sends requests through Worker 3 and Worker 0 -> 200 OK
        rb1 = await self.workers[3].handle_http_request("/api/orders", "POST", gateway_ip, {"x-forwarded-for": client_b})
        rb2 = await self.workers[0].handle_http_request("/api/orders", "POST", gateway_ip, {"x-forwarded-for": client_b})
        assert rb1.status_code == 200
        assert rb2.status_code == 200
