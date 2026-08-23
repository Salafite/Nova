import asyncio
from concurrent.futures import ThreadPoolExecutor
import pytest
from modules.core.context import (
    get_current_tenant,
    set_current_tenant,
    reset_current_tenant,
    clear_current_tenant,
    tenant_context,
)


def test_default_tenant_is_none():
    assert get_current_tenant() is None


def test_set_and_get_current_tenant():
    token = set_current_tenant(42)
    try:
        assert get_current_tenant() == 42
    finally:
        reset_current_tenant(token)
    assert get_current_tenant() is None


def test_reset_current_tenant():
    token1 = set_current_tenant(100)
    assert get_current_tenant() == 100
    token2 = set_current_tenant(200)
    assert get_current_tenant() == 200
    reset_current_tenant(token2)
    assert get_current_tenant() == 100
    reset_current_tenant(token1)
    assert get_current_tenant() is None


def test_clear_current_tenant():
    token1 = set_current_tenant(123)
    assert get_current_tenant() == 123
    token2 = clear_current_tenant()
    assert get_current_tenant() is None
    reset_current_tenant(token2)
    assert get_current_tenant() == 123
    reset_current_tenant(token1)
    assert get_current_tenant() is None


def test_tenant_context_manager():
    assert get_current_tenant() is None
    with tenant_context(55) as tenant_id:
        assert tenant_id == 55
        assert get_current_tenant() == 55
    assert get_current_tenant() is None


def test_nested_tenant_context_manager():
    with tenant_context(10):
        assert get_current_tenant() == 10
        with tenant_context(20):
            assert get_current_tenant() == 20
        assert get_current_tenant() == 10
    assert get_current_tenant() is None


def test_tenant_context_resets_on_exception():
    with pytest.raises(RuntimeError):
        with tenant_context(99):
            assert get_current_tenant() == 99
            raise RuntimeError("something went wrong")
    assert get_current_tenant() is None


def test_set_current_tenant_with_string_and_invalid_values():
    token = set_current_tenant("123")
    try:
        assert get_current_tenant() == 123
    finally:
        reset_current_tenant(token)

    token = set_current_tenant("invalid")
    try:
        assert get_current_tenant() is None
    finally:
        reset_current_tenant(token)

    token = set_current_tenant(None)
    try:
        assert get_current_tenant() is None
    finally:
        reset_current_tenant(token)


@pytest.mark.asyncio
async def test_async_task_context_isolation():
    async def worker(tenant_id: int):
        with tenant_context(tenant_id):
            await asyncio.sleep(0.01)
            assert get_current_tenant() == tenant_id
            return get_current_tenant()

    results = await asyncio.gather(
        worker(1),
        worker(2),
        worker(3),
    )
    assert results == [1, 2, 3]
    assert get_current_tenant() is None


def test_thread_context_isolation():
    def worker(tenant_id: int):
        with tenant_context(tenant_id):
            assert get_current_tenant() == tenant_id
            return get_current_tenant()

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(worker, i) for i in [10, 20, 30]]
        results = [f.result() for f in futures]

    assert results == [10, 20, 30]
    assert get_current_tenant() is None
