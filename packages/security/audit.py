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


def record_mcp_tool_execution(
    tool_name: str,
    arguments: Optional[dict] = None,
    result: Optional[Any] = None,
    status: str = "SUCCESS",
    user_id: Optional[int] = None,
    business_id: Optional[int] = None,
    role: Optional[str] = None,
    required_permission: Optional[str] = None,
    latency_ms: Optional[float] = None,
    error: Optional[str] = None,
    details: Optional[dict] = None,
) -> Optional[dict]:
    """
    Record an MCP tool execution (or denial/error) to the audit logger and T0023 audit table.

    Args:
        tool_name: Name of the executed MCP tool
        arguments: Tool invocation parameters / arguments
        result: Tool execution result or mutation output
        status: Execution status ('SUCCESS', 'DENIED', 'ERROR')
        user_id: ID of the user executing the tool
        business_id: Tenant / business context ID
        role: User role
        required_permission: Permission required by the tool
        latency_ms: Execution duration in milliseconds
        error: Error message if failed/denied
        details: Additional contextual metadata

    Returns:
        The created T0023 audit record dictionary if saved, or None on failure.
    """
    tenant_id = business_id if business_id is not None else get_current_tenant()

    record_id = 0
    if isinstance(arguments, dict):
        if "id" in arguments and isinstance(arguments["id"], int):
            record_id = arguments["id"]
        elif "record_id" in arguments and isinstance(arguments["record_id"], int):
            record_id = arguments["record_id"]

    log_payload = {
        "event": "mcp_tool_execution",
        "tool_name": tool_name,
        "arguments": arguments or {},
        "status": status,
        "user_id": user_id,
        "role": role,
        "tenant_id": tenant_id,
        "required_permission": required_permission,
        "latency_ms": latency_ms,
        "result": result,
        "error": error,
        "details": details or {},
    }

    action_str = f"MCP_{status.upper()}"[:20]

    if status == "DENIED":
        logger.warning(
            "MCP tool [%s] DENIED for user=%s (role=%s, tenant=%s, required_permission=%s, latency_ms=%s): error=%s",
            tool_name,
            user_id,
            role,
            tenant_id,
            required_permission,
            latency_ms,
            error,
        )
    elif status == "ERROR":
        logger.error(
            "MCP tool [%s] ERROR for user=%s (role=%s, tenant=%s, latency_ms=%s): error=%s",
            tool_name,
            user_id,
            role,
            tenant_id,
            latency_ms,
            error,
        )
    else:
        logger.info(
            "MCP tool [%s] SUCCESS for user=%s (role=%s, tenant=%s, latency_ms=%s)",
            tool_name,
            user_id,
            role,
            tenant_id,
            latency_ms,
        )

    try:
        data_str = json.dumps(log_payload, default=_json_safe)
        entry = {
            'table_name': 'MCP_TOOL',
            'record_id': record_id,
            'action': action_str,
            'changed_data': data_str,
            'changed_by': user_id,
            'changed_at': datetime.now(timezone.utc).isoformat(),
        }
        if tenant_id is not None:
            entry['business_id'] = tenant_id

        return _audit_repo.create(entry, business_id=tenant_id)
    except Exception as e:
        logger.error("Failed to persist MCP tool audit event to T0023: %s", str(e))
        return None


def record_mcp_propose_confirm(
    action_type: str,
    tool_name: str,
    action_id: str,
    arguments: Optional[dict] = None,
    preview: Optional[str] = None,
    result: Optional[Any] = None,
    status: str = "SUCCESS",
    user_id: Optional[int] = None,
    business_id: Optional[int] = None,
    role: Optional[str] = None,
    error: Optional[str] = None,
    details: Optional[dict] = None,
) -> Optional[dict]:
    """
    Record a Tier-2 MCP propose or confirm action event to the audit logger and T0023 audit table.

    Args:
        action_type: Type of action ('PROPOSE', 'CONFIRM', 'EXPIRE', 'DENIED')
        tool_name: Name of the tier-2 MCP tool
        action_id: Unique action UUID
        arguments: Tool invocation arguments
        preview: Action preview string
        result: Execution result if confirmed
        status: Status ('SUCCESS', 'DENIED', 'ERROR')
        user_id: ID of the user proposing/confirming
        business_id: Tenant / business context ID
        role: User role
        error: Error message if any
        details: Additional context metadata

    Returns:
        The created T0023 audit record dictionary if saved, or None on failure.
    """
    tenant_id = business_id if business_id is not None else get_current_tenant()

    record_id = 0
    if isinstance(arguments, dict):
        if "id" in arguments and isinstance(arguments["id"], int):
            record_id = arguments["id"]
        elif "record_id" in arguments and isinstance(arguments["record_id"], int):
            record_id = arguments["record_id"]

    log_payload = {
        "event": "mcp_propose_confirm",
        "action_type": action_type,
        "action_id": action_id,
        "tool_name": tool_name,
        "arguments": arguments or {},
        "preview": preview,
        "result": result,
        "status": status,
        "user_id": user_id,
        "role": role,
        "tenant_id": tenant_id,
        "error": error,
        "details": details or {},
    }

    action_label = f"MCP_{action_type.upper()}"[:20]

    if status == "DENIED":
        logger.warning(
            "MCP action [%s:%s] DENIED for user=%s (role=%s, tenant=%s): tool=%s, error=%s",
            action_type,
            action_id,
            user_id,
            role,
            tenant_id,
            tool_name,
            error,
        )
    elif status == "ERROR":
        logger.error(
            "MCP action [%s:%s] ERROR for user=%s (role=%s, tenant=%s): tool=%s, error=%s",
            action_type,
            action_id,
            user_id,
            role,
            tenant_id,
            tool_name,
            error,
        )
    else:
        logger.info(
            "MCP action [%s:%s] SUCCESS for user=%s (role=%s, tenant=%s): tool=%s",
            action_type,
            action_id,
            user_id,
            role,
            tenant_id,
            tool_name,
        )

    try:
        data_str = json.dumps(log_payload, default=_json_safe)
        entry = {
            'table_name': 'MCP_ACTION',
            'record_id': record_id,
            'action': action_label,
            'changed_data': data_str,
            'changed_by': user_id,
            'changed_at': datetime.now(timezone.utc).isoformat(),
        }
        if tenant_id is not None:
            entry['business_id'] = tenant_id

        return _audit_repo.create(entry, business_id=tenant_id)
    except Exception as e:
        logger.error("Failed to persist MCP propose/confirm audit event to T0023: %s", str(e))
        return None


# Aliases for compatibility
def log_security_event(*args, **kwargs):
    return record_security_event(*args, **kwargs)


def log_cross_tenant_access(*args, **kwargs):
    return record_security_event(*args, **kwargs)


def record_cross_tenant_attempt(*args, **kwargs):
    return record_security_event(*args, **kwargs)


