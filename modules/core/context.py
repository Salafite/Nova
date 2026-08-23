import contextvars
from contextlib import contextmanager
from typing import Generator, Optional, Union

# Context variable for the active tenant ID (business_id)
_current_tenant: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "current_tenant", default=None
)


def get_current_tenant() -> Optional[int]:
    """Return the active tenant ID (business_id) in the current context, or None if unset."""
    return _current_tenant.get()


def set_current_tenant(tenant_id: Optional[Union[int, str]]) -> contextvars.Token:
    """Set the active tenant ID (business_id) in the current context.

    Accepts an integer, numeric string, or None.
    Returns a contextvars.Token that can be passed to reset_current_tenant.
    """
    val: Optional[int] = None
    if tenant_id is not None:
        try:
            val = int(tenant_id)
        except (ValueError, TypeError):
            val = None
    return _current_tenant.set(val)


def reset_current_tenant(token: contextvars.Token) -> None:
    """Reset the tenant context variable to the state before set_current_tenant was called."""
    try:
        _current_tenant.reset(token)
    except ValueError:
        # Token was created in a different Context (e.g. across async/thread generator steps)
        pass


def clear_current_tenant() -> contextvars.Token:
    """Clear the active tenant ID in the current context (sets it to None)."""
    return _current_tenant.set(None)


@contextmanager
def tenant_context(tenant_id: Optional[Union[int, str]]) -> Generator[Optional[int], None, None]:
    """Context manager for temporarily setting the active tenant ID.

    Usage:
        with tenant_context(business_id):
            # operations within this block will see get_current_tenant() == business_id
            ...
    """
    token = set_current_tenant(tenant_id)
    try:
        yield get_current_tenant()
    finally:
        reset_current_tenant(token)
