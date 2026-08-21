from __future__ import annotations

import ipaddress
import logging
import os
import threading
import time
import uuid
from collections import defaultdict
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from packages.redis.client import get_redis_client

logger = logging.getLogger("nova.rate_limit")

RATE_LIMITS: dict[str, tuple[int, int | float]] = {
    'auth': (10, 1),
    'read': (100, 1),
    'ai': (10, 1),
    'write': (50, 1),
}

RATE_LIMIT_KEY_PREFIX = "nova:ratelimit:"


def _classify(path: str, method: str) -> str:
    if path.startswith('/api/auth/'):
        return 'auth'
    if path.startswith('/api/ai/'):
        return 'ai'
    if method in ('GET',):
        return 'read'
    return 'write'


def parse_trusted_proxies(trusted_proxies: list[str] | str | None = None) -> list[str]:
    """Parse trusted proxies from argument or TRUSTED_PROXIES environment variable."""
    if trusted_proxies is None:
        trusted_env = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1")
        raw_list = trusted_env.split(",")
    elif isinstance(trusted_proxies, str):
        raw_list = trusted_proxies.split(",")
    else:
        raw_list = list(trusted_proxies)

    return [item.strip() for item in raw_list if item.strip()]


def _clean_ip(ip_str: str) -> str:
    """Strip whitespace, quotes, and optional port/brackets from an IP string."""
    if not ip_str:
        return ""
    ip_str = ip_str.strip().strip("'\"")
    if not ip_str:
        return ""

    # Bracketed IPv6: [2001:db8::1]:8080 or [2001:db8::1]
    if ip_str.startswith("["):
        end_idx = ip_str.find("]")
        if end_idx != -1:
            return ip_str[1:end_idx].strip()

    # IPv4 with port: 1.2.3.4:8080
    if ":" in ip_str and ip_str.count(":") == 1:
        host, _, _ = ip_str.partition(":")
        try:
            ipaddress.IPv4Address(host.strip())
            return host.strip()
        except ValueError:
            pass

    return ip_str


def _to_ip_address(ip_str: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Parse an IP string into an IPAddress object, unwrapping IPv4-mapped IPv6."""
    cleaned = _clean_ip(ip_str)
    if not cleaned:
        return None
    try:
        ip = ipaddress.ip_address(cleaned)
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
            return ip.ipv4_mapped
        return ip
    except ValueError:
        return None


def is_ip_trusted(ip_str: str, trusted_proxies: list[str]) -> bool:
    """Check if an IP address matches any trusted proxy IP or subnet."""
    if not ip_str or not trusted_proxies:
        return False

    cleaned = _clean_ip(ip_str)
    if not cleaned:
        return False

    for item in trusted_proxies:
        item = item.strip()
        if not item:
            continue
        if item in ("*", "all", "0.0.0.0/0", "::/0"):
            return True

    ip = _to_ip_address(cleaned)
    if ip is None:
        return False

    for item in trusted_proxies:
        item = item.strip()
        if not item or item in ("*", "all", "0.0.0.0/0", "::/0"):
            continue
        try:
            if "/" in item:
                net = ipaddress.ip_network(item, strict=False)
                if ip.version == net.version and ip in net:
                    return True
            else:
                trusted_cleaned = _clean_ip(item)
                trusted_ip = _to_ip_address(trusted_cleaned)
                if trusted_ip is not None and ip == trusted_ip:
                    return True
        except ValueError:
            continue

    return False


def _extract_header(request: Any, name: str) -> str | None:
    """Safely extract header value from request, checking headers mapping and ASGI scope."""
    if hasattr(request, "headers") and request.headers is not None:
        try:
            val = (
                request.headers.get(name)
                or request.headers.get(name.lower())
                or request.headers.get(name.title())
            )
            if val:
                return str(val).strip()
            if hasattr(request.headers, "getlist"):
                values = request.headers.getlist(name) or request.headers.getlist(name.lower())
                if values:
                    return ", ".join(str(v).strip() for v in values if str(v).strip())
        except Exception:
            pass

    scope = getattr(request, "scope", None)
    if isinstance(scope, dict):
        raw_headers = scope.get("headers")
        if isinstance(raw_headers, (list, tuple)):
            target = name.lower().encode("latin-1")
            matches = [v.decode("latin-1").strip() for k, v in raw_headers if k.lower() == target]
            if matches:
                return ", ".join(matches)

    return None


def _extract_peer_ip(request: Any) -> str | None:
    """Extract immediate peer IP from request.client or ASGI scope."""
    if hasattr(request, "client") and request.client is not None:
        client = request.client
        if hasattr(client, "host") and isinstance(client.host, str) and client.host.strip():
            return _clean_ip(client.host)
        if isinstance(client, (tuple, list)) and len(client) > 0 and isinstance(client[0], str):
            return _clean_ip(client[0])
        if isinstance(client, str) and client.strip():
            return _clean_ip(client)

    scope = getattr(request, "scope", None)
    if isinstance(scope, dict):
        client = scope.get("client")
        if isinstance(client, (tuple, list)) and len(client) > 0 and isinstance(client[0], str):
            return _clean_ip(client[0])

    return None


def extract_client_ip(request: Any, trusted_proxies: list[str] | str | None = None) -> str:
    """Extract client IP from request, honoring X-Forwarded-For and X-Real-IP when from trusted proxies."""
    trusted_list = parse_trusted_proxies(trusted_proxies)
    peer_ip = _extract_peer_ip(request)

    # Safely extract proxy headers
    xff = _extract_header(request, "x-forwarded-for")
    x_real_ip = _extract_header(request, "x-real-ip")

    # If peer IP is trusted (or peer_ip is None in test mocks), we trust proxy headers
    if peer_ip is None or is_ip_trusted(peer_ip, trusted_list):
        if xff:
            ips = [_clean_ip(ip) for ip in xff.split(",") if _clean_ip(ip)]
            if ips:
                # Traverse right-to-left across proxy chain:
                # The first IP from the right that is NOT in trusted_proxies is the authentic client IP
                for ip in reversed(ips):
                    if not is_ip_trusted(ip, trusted_list):
                        return ip
                # If all IPs in chain are trusted, return the leftmost original client
                return ips[0]

        if x_real_ip:
            cleaned_real = _clean_ip(x_real_ip)
            if cleaned_real:
                return cleaned_real

        if peer_ip is not None:
            return peer_ip

        return "127.0.0.1"

    # Peer is an untrusted direct client; ignore spoofable headers
    return peer_ip


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Any,
        trusted_proxies: list[str] | str | None = None,
        redis_client: Any = None,
    ) -> None:
        super().__init__(app)
        self._lock = threading.Lock()
        self._buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        self._redis_client = redis_client
        self._trusted_proxies = parse_trusted_proxies(trusted_proxies)

    def _get_redis(self) -> Any:
        if self._redis_client is not None:
            return self._redis_client
        return get_redis_client()

    def _check_rate_limit_redis(
        self, client_ip: str, category: str, limit: int, window: int | float, now: float
    ) -> tuple[bool, int]:
        """Check rate limit using Redis ZSET sliding window counter.

        Returns (is_allowed, retry_after).
        """
        redis_client = self._get_redis()
        key = f"{RATE_LIMIT_KEY_PREFIX}{client_ip}:{category}"
        clear_before = now - window

        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, "-inf", clear_before)
        pipe.zcard(key)
        pipe.zrange(key, 0, 0, withscores=True)
        results = pipe.execute()

        current_count = int(results[1])
        oldest_entries = results[2]

        if current_count >= limit:
            retry_after = 1
            if oldest_entries:
                try:
                    oldest_score = float(oldest_entries[0][1])
                    retry_after = max(1, int(oldest_score - now + window))
                except (IndexError, TypeError, ValueError):
                    retry_after = 1
            return False, retry_after

        # Record this request
        member = f"{now}:{uuid.uuid4().hex}"
        ttl_seconds = max(int(window * 2), 60)
        pipe = redis_client.pipeline()
        pipe.zadd(key, {member: now})
        pipe.expire(key, ttl_seconds)
        pipe.execute()

        return True, 0

    def _check_rate_limit_memory(
        self, client_ip: str, category: str, limit: int, window: int | float, now: float
    ) -> tuple[bool, int]:
        """Fallback in-memory rate limiting."""
        with self._lock:
            bucket = self._buckets[client_ip][category]
            bucket[:] = [t for t in bucket if t > now - window]
            if len(bucket) >= limit:
                retry_after = int(bucket[0] - now + window) if bucket else 1
                return False, max(retry_after, 1)
            bucket.append(now)
            return True, 0

    async def dispatch(self, request: Any, call_next: Any) -> Any:
        # Re-fetch trusted proxies in case environment variable changed dynamically
        trusted_proxies = parse_trusted_proxies(self._trusted_proxies)
        client_ip = extract_client_ip(request, trusted_proxies)
        category = _classify(request.url.path, request.method)
        limit, window = RATE_LIMITS.get(category, (50, 1))
        now = time.time()

        is_allowed = True
        retry_after = 1

        try:
            is_allowed, retry_after = self._check_rate_limit_redis(
                client_ip, category, limit, window, now
            )
        except Exception as e:
            logger.warning("Redis rate limit check failed (%s); using in-memory fallback.", str(e))
            is_allowed, retry_after = self._check_rate_limit_memory(
                client_ip, category, limit, window, now
            )

        if not is_allowed:
            return JSONResponse(
                status_code=429,
                content={'detail': 'Rate limit exceeded. Try again later.'},
                headers={'Retry-After': str(max(retry_after, 1))},
            )

        response = await call_next(request)
        return response
