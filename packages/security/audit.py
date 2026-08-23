import json
import logging
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Any, Optional

from modules.core.context import get_current_tenant
from modules.core.repositories.base import CrudRepository

logger = logging.getLogger("security.audit")

_audit_repo = CrudRepository(
    'T0023',
    pk='id',
    business_columns=['id', 'table_name', 'record_id', 'action', 'changed_data', 'changed_by', 'changed_at', 'business_id']
)


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    if hasattr(obj, 'model_dump') and callable(obj.model_dump):
        return obj.model_dump()
    if hasattr(obj, 'dict') and callable(obj.dict):
        return obj.dict()
    raise TypeError(f'Object of type {type(obj)} is not JSON serializable')


def record_security_event(
    table_name: str,
    record_id: int,
    action: str = "UNAUTHORIZED_ACCESS",
    user_id: Optional[int] = None,
    business_id: Optional[int] = None,
    target_tenant_id: Optional[int] = None,
    details: Optional[dict] = None,
) -> Optional[dict]:
    """
    Log an unauthorized or cross-tenant security event to the security logger and record it in T0023 audit table.

    Args:
        table_name: Database table name (e.g., 'T0001', 'T0010')
        record_id: Target record ID
        action: Security action/event type (e.g., 'CROSS_TENANT_ACCESS', 'UNAUTHORIZED_ACCESS')
        user_id: ID of the user attempting the access
        business_id: Active tenant ID of the user/context
        target_tenant_id: Actual tenant ID owner of the target record
        details: Additional context details dictionary

    Returns:
        The created T0023 audit record dictionary if saved, or None on failure.
    """
    tenant_id = business_id if business_id is not None else get_current_tenant()

    log_payload = {
        "event": "security_audit",
        "action": action,
        "table_name": table_name,
        "record_id": record_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "target_tenant_id": target_tenant_id,
        "details": details or {},
    }

    logger.warning(
        "Security event [%s] on %s id=%s by user=%s (tenant=%s, target_tenant=%s): %s",
        action,
        table_name,
        record_id,
        user_id,
        tenant_id,
        target_tenant_id,
        json.dumps(details or {}, default=_json_safe),
    )

    try:
        data_str = json.dumps(log_payload, default=_json_safe)
        entry = {
            'table_name': (table_name or 'UNKNOWN')[:10],
            'record_id': record_id,
            'action': (action or 'UNAUTHORIZED_ACCESS')[:20],
            'changed_data': data_str,
            'changed_by': user_id,
            'changed_at': datetime.now(timezone.utc).isoformat(),
        }
        if tenant_id is not None:
            entry['business_id'] = tenant_id

        return _audit_repo.create(entry, business_id=tenant_id)
    except Exception as e:
        logger.error("Failed to persist security audit event to T0023: %s", str(e))
        return None


# Aliases for compatibility
def log_security_event(*args, **kwargs):
    return record_security_event(*args, **kwargs)


def log_cross_tenant_access(*args, **kwargs):
    return record_security_event(*args, **kwargs)


def record_cross_tenant_attempt(*args, **kwargs):
    return record_security_event(*args, **kwargs)

