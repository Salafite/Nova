"""Unit tests for Redis client connection, configuration, and fallback mechanisms."""

import time
from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from packages.redis.client import (
    InMemoryPipeline,
    InMemoryRedis,
    _create_redis_pool,
    check_redis_health,
    get_redis_client,
    get_redis_config,
    ping_redis,
    reset_redis_client,
)


@pytest.fixture(autouse=True)
def clean_redis_state():
    """Reset Redis client singleton state before and after each test."""
    reset_redis_client()
    yield
    reset_redis_client()


class TestRedisConfig:
    """Tests for Redis configuration parsing from environment variables."""

    def test_default_environment_variables_parsed_correctly(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.delenv("REDIS_HOST", raising=False)
        monkeypatch.delenv("REDIS_PORT", raising=False)
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)
        monkeypatch.delenv("REDIS_DB", raising=False)
        monkeypatch.delenv("REDIS_MOCK", raising=False)
        monkeypatch.delenv("REDIS_USE_MOCK", raising=False)
        monkeypatch.delenv("REDIS_FALLBACK", raising=False)

        config = get_redis_config()

        assert config["url"] is None
        assert config["host"] == "localhost"
        assert config["port"] == 6379
        assert config["password"] is None
        assert config["db"] == 0
        assert config["mock"] is False
        assert config["fallback"] is True

    def test_custom_environment_variables_parsed_correctly(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "redis.internal.net")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_PASSWORD", "secret123")
        monkeypatch.setenv("REDIS_DB", "2")
        monkeypatch.setenv("REDIS_SOCKET_TIMEOUT", "3.5")
        monkeypatch.setenv("REDIS_MAX_CONNECTIONS", "100")
        monkeypatch.setenv("REDIS_FALLBACK", "false")

        config = get_redis_config()

        assert config["host"] == "redis.internal.net"
        assert config["port"] == 6380
        assert config["password"] == "secret123"
        assert config["db"] == 2
        assert config["socket_timeout"] == 3.5
        assert config["max_connections"] == 100
        assert config["fallback"] is False

    def test_redis_url_environment_variable_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://:pwd@redis.cluster:6381/3")

        config = get_redis_config()

        assert config["url"] == "redis://:pwd@redis.cluster:6381/3"

    @pytest.mark.parametrize("env_var,env_val,expected", [
        ("REDIS_MOCK", "true", True),
        ("REDIS_MOCK", "1", True),
        ("REDIS_MOCK", "false", False),
        ("REDIS_USE_MOCK", "yes", True),
        ("REDIS_USE_MOCK", "0", False),
    ])
    def test_mock_environment_flag_variants(self, monkeypatch, env_var, env_val, expected):
        monkeypatch.delenv("REDIS_MOCK", raising=False)
        monkeypatch.delenv("REDIS_USE_MOCK", raising=False)
        monkeypatch.setenv(env_var, env_val)

        config = get_redis_config()

        assert config["mock"] is expected


class TestRedisPoolInitialization:
    """Tests for Redis connection pool creation."""

    @patch("redis.ConnectionPool.from_url")
    def test_create_pool_from_url(self, mock_from_url):
        config = {
            "url": "redis://localhost:6379/1",
            "max_connections": 25,
            "socket_timeout": 1.5,
            "socket_connect_timeout": 1.5,
        }

        _create_redis_pool(config)

        mock_from_url.assert_called_once_with(
            "redis://localhost:6379/1",
            max_connections=25,
            socket_timeout=1.5,
            socket_connect_timeout=1.5,
            decode_responses=True,
        )

    @patch("redis.ConnectionPool.__init__", return_value=None)
    def test_create_pool_from_host_port(self, mock_init):
        config = {
            "url": None,
            "host": "10.0.0.5",
            "port": 6380,
            "password": "pwd",
            "db": 1,
            "max_connections": 30,
            "socket_timeout": 2.0,
            "socket_connect_timeout": 2.0,
        }

        _create_redis_pool(config)

        mock_init.assert_called_once_with(
            host="10.0.0.5",
            port=6380,
            password="pwd",
            db=1,
            max_connections=30,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
            decode_responses=True,
        )


class TestGetRedisClient:
    """Tests for get_redis_client instantiation, pooling, and fallbacks."""

    def test_explicit_use_mock_returns_in_memory_instance(self):
        client = get_redis_client(use_mock=True)

        assert isinstance(client, InMemoryRedis)

    def test_env_use_mock_returns_in_memory_instance(self, monkeypatch):
        monkeypatch.setenv("REDIS_MOCK", "true")

        client = get_redis_client()

        assert isinstance(client, InMemoryRedis)

    @patch("redis.Redis")
    @patch("packages.redis.client._create_redis_pool")
    def test_successful_connection_returns_redis_client(self, mock_create_pool, mock_redis_cls):
        mock_instance = MagicMock()
        mock_instance.ping.return_value = True
        mock_redis_cls.return_value = mock_instance

        client = get_redis_client(use_mock=False)

        assert client is mock_instance
        mock_instance.ping.assert_called_once()

    @patch("redis.Redis")
    @patch("packages.redis.client._create_redis_pool")
    def test_connection_failure_with_fallback_returns_in_memory_client(
        self, mock_create_pool, mock_redis_cls, monkeypatch
    ):
        monkeypatch.setenv("REDIS_FALLBACK", "true")
        mock_instance = MagicMock()
        mock_instance.ping.side_effect = RedisConnectionError("Connection refused")
        mock_redis_cls.return_value = mock_instance

        client = get_redis_client(use_mock=False)

        assert isinstance(client, InMemoryRedis)

    @patch("redis.Redis")
    @patch("packages.redis.client._create_redis_pool")
    def test_connection_failure_without_fallback_raises_error(
        self, mock_create_pool, mock_redis_cls, monkeypatch
    ):
        monkeypatch.setenv("REDIS_FALLBACK", "false")
        mock_instance = MagicMock()
        mock_instance.ping.side_effect = RedisConnectionError("Connection refused")
        mock_redis_cls.return_value = mock_instance

        with pytest.raises(RedisConnectionError, match="Connection refused"):
            get_redis_client(use_mock=False)

    @patch("redis.Redis")
    @patch("packages.redis.client._create_redis_pool")
    def test_singleton_client_reuse(self, mock_create_pool, mock_redis_cls):
        mock_instance = MagicMock()
        mock_instance.ping.return_value = True
        mock_redis_cls.return_value = mock_instance

        client1 = get_redis_client(use_mock=False)
        client2 = get_redis_client(use_mock=False)

        assert client1 is client2
        assert mock_redis_cls.call_count == 1


class TestPingRedisAndHealthCheck:
    """Tests for ping_redis and check_redis_health functions."""

    def test_ping_in_memory_redis_returns_true(self):
        client = InMemoryRedis()
        assert ping_redis(client) is True

    def test_ping_healthy_redis_returns_true(self):
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        assert ping_redis(mock_client) is True

    @pytest.mark.parametrize("error_cls", [RedisConnectionError, RedisTimeoutError, OSError])
    def test_ping_unhealthy_redis_returns_false(self, error_cls):
        mock_client = MagicMock()
        mock_client.ping.side_effect = error_cls("Server down")

        assert ping_redis(mock_client) is False

    def test_health_check_healthy_status(self):
        client = InMemoryRedis()

        health = check_redis_health(client)

        assert health["status"] == "healthy"
        assert health["connected"] is True
        assert health["backend"] == "mock"
        assert health["latency_ms"] >= 0
        assert health["error"] is None

    def test_health_check_unhealthy_status(self):
        mock_client = MagicMock()
        mock_client.ping.side_effect = RedisConnectionError("Host unreachable")

        health = check_redis_health(mock_client)

        assert health["status"] == "unhealthy"
        assert health["connected"] is False
        assert health["backend"] == "redis"
        assert health["error"] == "Ping failed"


class TestInMemoryRedisOperations:
    """Tests for InMemoryRedis functionality, matching redis-py APIs."""

    def test_key_value_set_get_delete(self):
        client = InMemoryRedis()

        client.set("foo", "bar")
        assert client.get("foo") == "bar"
        assert client.exists("foo") == 1

        deleted = client.delete("foo")
        assert deleted == 1
        assert client.get("foo") is None
        assert client.exists("foo") == 0

    def test_getdel_atomically_fetches_and_deletes(self):
        client = InMemoryRedis()
        client.set("action:123", "payload_data")

        fetched = client.getdel("action:123")
        assert fetched == "payload_data"
        assert client.get("action:123") is None

        # Second call returns None
        assert client.getdel("action:123") is None

    def test_ttl_expiry_removes_key_after_duration(self):
        client = InMemoryRedis()
        client.set("temp_key", "value", ex=0.05)

        assert client.get("temp_key") == "value"
        assert client.ttl("temp_key") >= 0

        time.sleep(0.06)

        assert client.get("temp_key") is None
        assert client.ttl("temp_key") == -2
        assert client.exists("temp_key") == 0

    def test_expire_and_pexpire_set_ttl(self):
        client = InMemoryRedis()
        client.set("key1", "val")
        assert client.ttl("key1") == -1

        client.expire("key1", 10)
        assert client.ttl("key1") > 0

        client.pexpire("key1", 5000)
        assert client.pttl("key1") > 0

    def test_keys_pattern_matching(self):
        client = InMemoryRedis()
        client.set("nova:mcp:action:1", "a")
        client.set("nova:mcp:action:2", "b")
        client.set("nova:ratelimit:auth:ip", "c")

        actions = client.keys("nova:mcp:action:*")
        assert sorted(actions) == ["nova:mcp:action:1", "nova:mcp:action:2"]

        all_keys = client.keys("*")
        assert len(all_keys) == 3

    def test_sorted_set_sliding_window_operations(self):
        client = InMemoryRedis()
        zset_key = "ratelimit:127.0.0.1:auth"

        # Add timestamps to ZSET
        client.zadd(zset_key, {"req1": 1000.0, "req2": 1001.0, "req3": 1005.0})
        assert client.zcard(zset_key) == 3

        # Remove entries older than 1002.0
        removed = client.zremrangebyscore(zset_key, "-inf", 1002.0)
        assert removed == 2
        assert client.zcard(zset_key) == 1

        # Check remaining
        remaining = client.zrange(zset_key, 0, -1)
        assert remaining == ["req3"]

    def test_hashes_operations(self):
        client = InMemoryRedis()
        client.hset("user:1", "name", "Alice")
        client.hset("user:1", mapping={"email": "alice@test.com", "role": "admin"})

        assert client.hget("user:1", "name") == "Alice"
        assert client.hexists("user:1", "role") is True
        assert client.hgetall("user:1") == {
            "name": "Alice",
            "email": "alice@test.com",
            "role": "admin",
        }

        client.hdel("user:1", "role")
        assert client.hexists("user:1", "role") is False

    def test_pipeline_atomic_execution(self):
        client = InMemoryRedis()
        pipe = client.pipeline()

        pipe.set("k1", "v1")
        pipe.set("k2", "v2")
        pipe.get("k1")
        pipe.zadd("z1", {"m1": 1.0, "m2": 2.0})
        pipe.zcard("z1")

        results = pipe.execute()

        assert results == [True, True, "v1", 2, 2]
        assert client.get("k1") == "v1"
        assert client.get("k2") == "v2"
        assert client.zcard("z1") == 2

    def test_flushdb_clears_all_structures(self):
        client = InMemoryRedis()
        client.set("k1", "v1")
        client.zadd("z1", {"m1": 1.0})
        client.hset("h1", "f1", "v1")

        client.flushdb()

        assert client.get("k1") is None
        assert client.zcard("z1") == 0
        assert client.hgetall("h1") == {}
