"""Centralized Redis client module for Nova ERP.

Provides connection pooling, configuration management, health checking,
and an in-memory fallback client for offline/test environments.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import threading
import time
from typing import Any

import redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError

logger = logging.getLogger("nova.redis")

_pool: redis.ConnectionPool | None = None
_client: redis.Redis | None = None
_mock_client: InMemoryRedis | None = None
_lock = threading.Lock()


def get_redis_config() -> dict[str, Any]:
    """Retrieve Redis configuration from environment variables."""
    redis_url = os.getenv("REDIS_URL", "").strip() or None
    redis_host = os.getenv("REDIS_HOST", "localhost").strip()
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_password = os.getenv("REDIS_PASSWORD", "").strip() or None
    redis_db = int(os.getenv("REDIS_DB", 0))
    socket_timeout = float(os.getenv("REDIS_SOCKET_TIMEOUT", 2.0))
    socket_connect_timeout = float(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", 2.0))
    max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", 50))
    use_mock_env = os.getenv("REDIS_MOCK", "").lower() in ("true", "1", "yes") or \
                   os.getenv("REDIS_USE_MOCK", "").lower() in ("true", "1", "yes")
    fallback_env = os.getenv("REDIS_FALLBACK", "true").lower() in ("true", "1", "yes")

    return {
        "url": redis_url,
        "host": redis_host,
        "port": redis_port,
        "password": redis_password,
        "db": redis_db,
        "socket_timeout": socket_timeout,
        "socket_connect_timeout": socket_connect_timeout,
        "max_connections": max_connections,
        "mock": use_mock_env,
        "fallback": fallback_env,
    }


class InMemoryPipeline:
    """Thread-safe in-memory pipeline mimicking redis.client.Pipeline."""

    def __init__(self, in_memory_redis: InMemoryRedis) -> None:
        self._redis = in_memory_redis
        self._commands: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def set(self, name: str, value: Any, **kwargs: Any) -> InMemoryPipeline:
        self._commands.append(("set", (name, value), kwargs))
        return self

    def get(self, name: str) -> InMemoryPipeline:
        self._commands.append(("get", (name,), {}))
        return self

    def getdel(self, name: str) -> InMemoryPipeline:
        self._commands.append(("getdel", (name,), {}))
        return self

    def delete(self, *names: str) -> InMemoryPipeline:
        self._commands.append(("delete", names, {}))
        return self

    def exists(self, *names: str) -> InMemoryPipeline:
        self._commands.append(("exists", names, {}))
        return self

    def expire(self, name: str, time_sec: int) -> InMemoryPipeline:
        self._commands.append(("expire", (name, time_sec), {}))
        return self

    def ttl(self, name: str) -> InMemoryPipeline:
        self._commands.append(("ttl", (name,), {}))
        return self

    def zadd(self, name: str, mapping: dict[str, float], **kwargs: Any) -> InMemoryPipeline:
        self._commands.append(("zadd", (name, mapping), kwargs))
        return self

    def zremrangebyscore(self, name: str, min_score: float | str, max_score: float | str) -> InMemoryPipeline:
        self._commands.append(("zremrangebyscore", (name, min_score, max_score), {}))
        return self

    def zcard(self, name: str) -> InMemoryPipeline:
        self._commands.append(("zcard", (name,), {}))
        return self

    def zrange(self, name: str, start: int, end: int, **kwargs: Any) -> InMemoryPipeline:
        self._commands.append(("zrange", (name, start, end), kwargs))
        return self

    def execute(self) -> list[Any]:
        results: list[Any] = []
        with self._redis._lock:
            for method_name, args, kwargs in self._commands:
                method = getattr(self._redis, method_name)
                res = method(*args, **kwargs)
                results.append(res)
        self._commands.clear()
        return results

    def __enter__(self) -> InMemoryPipeline:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._commands.clear()


class InMemoryRedis:
    """Thread-safe in-memory Redis implementation for tests and standalone execution."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self._expiry: dict[str, float] = {}
        self._zsets: dict[str, dict[str, float]] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._lock = threading.RLock()

    def _purge_key_if_expired(self, key: str) -> bool:
        """Check if a key is expired, removing it if so. Returns True if expired."""
        if key in self._expiry:
            if time.time() > self._expiry[key]:
                self._data.pop(key, None)
                self._expiry.pop(key, None)
                self._zsets.pop(key, None)
                self._hashes.pop(key, None)
                return True
        return False

    def ping(self) -> bool:
        """Check availability."""
        return True

    def set(
        self,
        name: str,
        value: Any,
        ex: int | float | None = None,
        px: int | float | None = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool | None:
        with self._lock:
            self._purge_key_if_expired(name)
            exists = name in self._data or name in self._zsets or name in self._hashes
            if nx and exists:
                return None
            if xx and not exists:
                return None

            str_value = value if isinstance(value, str) else str(value)
            self._data[name] = str_value

            # Clean up other type structures if overwriting
            self._zsets.pop(name, None)
            self._hashes.pop(name, None)

            if ex is not None:
                self._expiry[name] = time.time() + float(ex)
            elif px is not None:
                self._expiry[name] = time.time() + (float(px) / 1000.0)
            else:
                self._expiry.pop(name, None)
            return True

    def get(self, name: str) -> str | None:
        with self._lock:
            if self._purge_key_if_expired(name):
                return None
            return self._data.get(name)

    def getdel(self, name: str) -> str | None:
        with self._lock:
            if self._purge_key_if_expired(name):
                return None
            val = self._data.pop(name, None)
            self._expiry.pop(name, None)
            return val

    def delete(self, *names: str) -> int:
        deleted = 0
        with self._lock:
            for name in names:
                self._purge_key_if_expired(name)
                existed = False
                if name in self._data:
                    del self._data[name]
                    existed = True
                if name in self._zsets:
                    del self._zsets[name]
                    existed = True
                if name in self._hashes:
                    del self._hashes[name]
                    existed = True
                self._expiry.pop(name, None)
                if existed:
                    deleted += 1
        return deleted

    def exists(self, *names: str) -> int:
        count = 0
        with self._lock:
            for name in names:
                if not self._purge_key_if_expired(name):
                    if name in self._data or name in self._zsets or name in self._hashes:
                        count += 1
        return count

    def expire(self, name: str, time_sec: int | float) -> bool:
        with self._lock:
            if self._purge_key_if_expired(name):
                return False
            if name in self._data or name in self._zsets or name in self._hashes:
                self._expiry[name] = time.time() + float(time_sec)
                return True
            return False

    def pexpire(self, name: str, time_ms: int | float) -> bool:
        return self.expire(name, float(time_ms) / 1000.0)

    def ttl(self, name: str) -> int:
        with self._lock:
            if self._purge_key_if_expired(name):
                return -2
            if name not in self._data and name not in self._zsets and name not in self._hashes:
                return -2
            if name not in self._expiry:
                return -1
            remaining = int(self._expiry[name] - time.time())
            return remaining if remaining >= 0 else -2

    def pttl(self, name: str) -> int:
        with self._lock:
            if self._purge_key_if_expired(name):
                return -2
            if name not in self._data and name not in self._zsets and name not in self._hashes:
                return -2
            if name not in self._expiry:
                return -1
            remaining = int((self._expiry[name] - time.time()) * 1000.0)
            return remaining if remaining >= 0 else -2

    def keys(self, pattern: str = "*") -> list[str]:
        with self._lock:
            all_keys = set(self._data.keys()) | set(self._zsets.keys()) | set(self._hashes.keys())
            active_keys = [k for k in all_keys if not self._purge_key_if_expired(k)]
            return [k for k in active_keys if fnmatch.fnmatch(k, pattern)]

    def flushdb(self) -> bool:
        with self._lock:
            self._data.clear()
            self._expiry.clear()
            self._zsets.clear()
            self._hashes.clear()
        return True

    def flushall(self) -> bool:
        return self.flushdb()

    def zadd(
        self,
        name: str,
        mapping: dict[str, float],
        nx: bool = False,
        xx: bool = False,
        ch: bool = False,
        incr: bool = False,
    ) -> int:
        with self._lock:
            self._purge_key_if_expired(name)
            if name not in self._zsets:
                self._zsets[name] = {}
            zset = self._zsets[name]
            added = 0
            for member, score in mapping.items():
                str_member = str(member)
                exists = str_member in zset
                if nx and exists:
                    continue
                if xx and not exists:
                    continue
                if not exists:
                    added += 1
                if incr and exists:
                    zset[str_member] = float(zset[str_member]) + float(score)
                else:
                    zset[str_member] = float(score)
            return added

    def zremrangebyscore(self, name: str, min_score: float | str, max_score: float | str) -> int:
        with self._lock:
            if self._purge_key_if_expired(name):
                return 0
            if name not in self._zsets:
                return 0
            zset = self._zsets[name]
            min_val = float("-inf") if str(min_score) in ("-inf", "-infinity") else float(min_score)
            max_val = float("inf") if str(max_score) in ("+inf", "+infinity", "inf", "infinity") else float(max_score)

            to_remove = [member for member, score in zset.items() if min_val <= score <= max_val]
            for member in to_remove:
                del zset[member]
            return len(to_remove)

    def zcard(self, name: str) -> int:
        with self._lock:
            if self._purge_key_if_expired(name):
                return 0
            return len(self._zsets.get(name, {}))

    def zrange(
        self,
        name: str,
        start: int,
        end: int,
        desc: bool = False,
        withscores: bool = False,
        score_cast_func: Any = float,
    ) -> list[Any]:
        with self._lock:
            if self._purge_key_if_expired(name):
                return []
            zset = self._zsets.get(name, {})
            sorted_items = sorted(zset.items(), key=lambda x: x[1], reverse=desc)
            length = len(sorted_items)
            if length == 0:
                return []

            if start < 0:
                start = max(0, length + start)
            if end < 0:
                end = length + end
            end = min(length - 1, end)

            if start > end or start >= length:
                return []

            sliced = sorted_items[start: end + 1]
            if withscores:
                return [(item[0], score_cast_func(item[1])) for item in sliced]
            return [item[0] for item in sliced]

    def zrangebyscore(
        self,
        name: str,
        min_score: float | str,
        max_score: float | str,
        withscores: bool = False,
    ) -> list[Any]:
        with self._lock:
            if self._purge_key_if_expired(name):
                return []
            zset = self._zsets.get(name, {})
            min_val = float("-inf") if str(min_score) in ("-inf", "-infinity") else float(min_score)
            max_val = float("inf") if str(max_score) in ("+inf", "+infinity", "inf", "infinity") else float(max_score)

            filtered = [(m, s) for m, s in zset.items() if min_val <= s <= max_val]
            sorted_items = sorted(filtered, key=lambda x: x[1])
            if withscores:
                return sorted_items
            return [item[0] for item in sorted_items]

    def zrem(self, name: str, *values: str) -> int:
        with self._lock:
            if self._purge_key_if_expired(name):
                return 0
            zset = self._zsets.get(name, {})
            removed = 0
            for val in values:
                if val in zset:
                    del zset[val]
                    removed += 1
            return removed

    def hset(
        self,
        name: str,
        key: str | None = None,
        value: Any = None,
        mapping: dict[str, Any] | None = None,
    ) -> int:
        with self._lock:
            self._purge_key_if_expired(name)
            if name not in self._hashes:
                self._hashes[name] = {}
            h = self._hashes[name]
            added = 0
            if mapping:
                for k, v in mapping.items():
                    if k not in h:
                        added += 1
                    h[k] = str(v)
            if key is not None and value is not None:
                if key not in h:
                    added += 1
                h[key] = str(value)
            return added

    def hget(self, name: str, key: str) -> str | None:
        with self._lock:
            if self._purge_key_if_expired(name):
                return None
            return self._hashes.get(name, {}).get(key)

    def hgetall(self, name: str) -> dict[str, str]:
        with self._lock:
            if self._purge_key_if_expired(name):
                return {}
            return dict(self._hashes.get(name, {}))

    def hdel(self, name: str, *keys: str) -> int:
        with self._lock:
            if self._purge_key_if_expired(name):
                return 0
            h = self._hashes.get(name, {})
            deleted = 0
            for k in keys:
                if k in h:
                    del h[k]
                    deleted += 1
            return deleted

    def hexists(self, name: str, key: str) -> bool:
        with self._lock:
            if self._purge_key_if_expired(name):
                return False
            return key in self._hashes.get(name, {})

    def pipeline(self, transaction: bool = True) -> InMemoryPipeline:
        return InMemoryPipeline(self)

    def close(self) -> None:
        pass


def _create_redis_pool(config: dict[str, Any]) -> redis.ConnectionPool:
    """Create a redis.ConnectionPool from config parameters."""
    if config["url"]:
        return redis.ConnectionPool.from_url(
            config["url"],
            max_connections=config["max_connections"],
            socket_timeout=config["socket_timeout"],
            socket_connect_timeout=config["socket_connect_timeout"],
            decode_responses=True,
        )

    return redis.ConnectionPool(
        host=config["host"],
        port=config["port"],
        password=config["password"],
        db=config["db"],
        max_connections=config["max_connections"],
        socket_timeout=config["socket_timeout"],
        socket_connect_timeout=config["socket_connect_timeout"],
        decode_responses=True,
    )


def get_redis_client(
    use_mock: bool | None = None,
    decode_responses: bool = True,
    force_new: bool = False,
) -> redis.Redis | InMemoryRedis:
    """Return a Redis client instance (real or in-memory fallback).

    If `use_mock=True` or `REDIS_MOCK=true`, an in-memory client is returned.
    If Redis server is unreachable and fallback is enabled, an in-memory client is returned.
    """
    global _pool, _client, _mock_client

    config = get_redis_config()
    should_mock = use_mock if use_mock is not None else config["mock"]

    if should_mock:
        with _lock:
            if _mock_client is None or force_new:
                _mock_client = InMemoryRedis()
            return _mock_client

    with _lock:
        if _client is not None and not force_new:
            return _client

        try:
            pool = _create_redis_pool(config)
            client = redis.Redis(connection_pool=pool, decode_responses=decode_responses)
            # Test connectivity
            client.ping()
            _pool = pool
            _client = client
            return _client
        except (RedisConnectionError, RedisTimeoutError, TimeoutError, OSError) as e:
            if config["fallback"]:
                logger.warning(
                    "Redis server at %s:%s unavailable (%s). Falling back to in-memory Redis.",
                    config["host"],
                    config["port"],
                    str(e),
                )
                if _mock_client is None or force_new:
                    _mock_client = InMemoryRedis()
                return _mock_client
            raise


def ping_redis(client: redis.Redis | InMemoryRedis | None = None) -> bool:
    """Ping Redis to test connectivity. Returns True if alive, False otherwise."""
    if client is None:
        try:
            client = get_redis_client()
        except Exception:
            return False

    try:
        res = client.ping()
        return bool(res)
    except (RedisError, TimeoutError, OSError):
        return False


def check_redis_health(client: redis.Redis | InMemoryRedis | None = None) -> dict[str, Any]:
    """Perform a health check on Redis, measuring latency and status."""
    start = time.time()
    try:
        if client is None:
            client = get_redis_client()

        backend = "mock" if isinstance(client, InMemoryRedis) else "redis"
        alive = ping_redis(client)
        latency_ms = round((time.time() - start) * 1000.0, 2)

        return {
            "status": "healthy" if alive else "unhealthy",
            "connected": alive,
            "backend": backend,
            "latency_ms": latency_ms,
            "error": None if alive else "Ping failed",
        }
    except Exception as e:
        latency_ms = round((time.time() - start) * 1000.0, 2)
        return {
            "status": "unhealthy",
            "connected": False,
            "backend": "unknown",
            "latency_ms": latency_ms,
            "error": str(e),
        }


def reset_redis_client() -> None:
    """Reset connection pool and clients for testing teardown or configuration changes."""
    global _pool, _client, _mock_client
    with _lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:
                pass
            _client = None
        if _pool is not None:
            try:
                _pool.disconnect()
            except Exception:
                pass
            _pool = None
        if _mock_client is not None:
            _mock_client.flushdb()
            _mock_client = None
