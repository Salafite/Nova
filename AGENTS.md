# Nova ERP — MCP & AI Architecture Guide

## Overview

Nova ERP serves two protocols side by side:

| Protocol | Audience | Purpose |
|----------|----------|---------|
| **REST API** (`/api/*`) | Vue 3 SPA | UI rendering, CRUD, auth |
| **MCP** (stdio/SSE) | AI agents | Natural language tool calling |

All 14 MCP server modules live under `packages/mcp/servers/`. Each module corresponds to an ERP domain and registers tools via the global registry (`packages/mcp/registry.py`).

## MCP Server List

| Server | Module | Tools |
|--------|--------|-------|
| database | `packages.mcp.servers.database_mcp` | `list_tables`, `describe_table`, `execute_read_query` |
| inventory | `packages.mcp.servers.inventory_mcp` | `list_products`, `get_product`, `create_product`, `update_product`, `delete_product`, `search_products`, `check_stock`, `list_categories`, `list_warehouses`, `list_uoms`, `list_brands` |
| sales | `packages.mcp.servers.sales_mcp` | `list_orders`, `get_order`, `create_order`, `update_order_status`, `confirm_order`, `cancel_order`, `list_customers`, `get_customer_aging`, `list_quotations`, `convert_quotation_to_order`, `list_deliveries`, `list_price_lists`, `list_tax_rates` |
| purchasing | `packages.mcp.servers.purchasing_mcp` | `list_purchase_orders`, `get_purchase_order`, `list_purchase_returns`, `list_rfqs` |
| accounting | `packages.mcp.servers.accounting_mcp` | `list_chart_of_accounts`, `list_invoices`, `get_invoice`, `list_payments`, `list_payment_terms` |
| admin | `packages.mcp.servers.admin_mcp` | `list_users`, `get_audit_log`, `list_settings`, `get_setting`, `list_notifications`, `list_scheduled_tasks`, `list_modules` |
| warehouse | `packages.mcp.servers.warehouse_mcp` | `list_goods_receipts`, `list_serial_numbers`, `list_batch_numbers`, `list_pick_lists` |
| hr | `packages.mcp.servers.hr_mcp` | `list_employees`, `get_employee`, `list_departments`, `list_attendance`, `list_leave_requests`, `list_payroll_entries`, `list_shifts`, `list_job_openings` |
| bi | `packages.mcp.servers.bi_mcp` | `list_kpis`, `get_kpi_values`, `list_dashboards`, `get_dashboard_widgets` |
| crm | `packages.mcp.servers.crm_mcp` | `list_leads`, `list_opportunities`, `list_suppliers`, `list_customer_groups` |
| projects | `packages.mcp.servers.projects_mcp` | `list_projects`, `get_project`, `list_tasks`, `list_milestones` |
| manufacturing | `packages.mcp.servers.manufacturing_mcp` | `list_manufacturing_orders`, `list_boms`, `list_qc_inspections`, `list_shop_jobs` |
| maintenance | `packages.mcp.servers.maintenance_mcp` | `list_assets`, `list_maintenance_schedules`, `list_work_orders` |
| notifications | `packages.mcp.servers.notifications_mcp` | `list_user_notifications`, `mark_notification_read`, `mark_all_notifications_read` |

## Running MCP Servers

### Stdio mode (for Claude Code, Cursor, etc.)

```bash
python -m packages.mcp.servers.inventory_mcp
```

Or use the launcher:

```bash
python scripts/run-mcp-server.py inventory
```

### SSE mode (for in-app AI)

```bash
python scripts/run-mcp-server.py inventory --port 8080
```

### Via opencode.json

All servers are registered in `opencode.json` — AI coding assistants that support MCP servers can use them directly.

## Auth & Context

### MCP Auth

- **SSE transport** (`/mcp/sse`, `/mcp/message`): Protected by `Depends(get_current_user)` — requires a valid JWT bearer token. Sessions are bound to the authenticated user.
- **Stdio transport**: No HTTP auth; uses env vars `NOVA_TENANT_ID`, `NOVA_API_KEY` (set at process launch).
- **AI assistant** (`POST /api/ai/chat`): Authenticated via JWT. The user context is forwarded to every MCP tool call via `contextvars`.

### User Context in Handlers

Tool handlers can access the current user via `get_current_user()` from `packages.mcp.registry`:

```python
from packages.mcp.registry import get_current_user

def _list_products(limit=50):
    user = get_current_user()  # dict with id, username, role, business_id or None
    ...
```

### Tenant Scoping (Known Gap)

**Finding:** No tenant scoping currently exists in any layer (controllers, services, or repositories). Most business tables lack a `business_id` column. Full tenant isolation requires:
1. Adding `business_id` to all business tables (schema migration)
2. Injecting tenant context in the service/repository layer
3. Adding `business_id` to the JWT payload for efficiency

Without this, MCP tools operate against all data regardless of tenant. Tools that accept `user_id` or `business_id` params must be called explicitly.

### Audit Logging

Every MCP tool call is logged via `packages/mcp/registry.call_tool()` with:
- `tool`, `user`, `tenant`, `status` (success/error), `latency_ms`
- Log output goes to the `mcp.audit` logger (configure via standard logging)

## Tool Safety Tiers

All 77 MCP tools are classified into two tiers:

| Tier | Policy | Count | Examples |
|------|--------|-------|---------|
| **Tier 1** | Direct execution (audit-logged) | 72 | All `list_*`, `get_*`, `check_*`, `search_*`, `create_*`, `update_*`, `mark_notification_read` |
| **Tier 2** | Requires propose/confirm | 5 | `delete_product`, `confirm_order`, `cancel_order`, `convert_quotation_to_order`, `mark_all_notifications_read` |

**Tier 2 behavior:** When the AI assistant calls a Tier 2 tool, it routes through `propose_action()` which returns an `action_id` and preview instead of executing. The UI shows the preview and requires user confirmation before `confirm_action(action_id)` executes the operation.

### Tier 2 Tools

| Tool | Server | Risk |
|------|--------|------|
| `delete_product` | inventory | Irreversible deletion |
| `confirm_order` | sales | Reserves stock, financial impact |
| `cancel_order` | sales | Releases stock, financial impact |
| `convert_quotation_to_order` | sales | Irreversible status change |
| `mark_all_notifications_read` | notifications | Bulk irreversible state change |

### Propose/Confirm Flow

```python
from packages.mcp.registry import propose_action, confirm_action

# Step 1: Propose (no execution)
result = propose_action("delete_product", {"id": 42})
# Returns: {"action_id": "abc-123", "preview": "...", "tool": "delete_product"}

# Step 2: Confirm (executes)
result = confirm_action("abc-123")
# Executes the handler and returns the result
```

Pending actions expire after 5 minutes.

## In-App AI Assistant

The AI assistant is integrated into the Nova ERP web UI:

- **Endpoint**: `POST /api/ai/chat` (SSE streaming, auth-protected)
- **LLM**: OpenAI GPT-4o (configurable via `OPENAI_MODEL`)
- **Tools**: All 77 MCP tools are exposed as OpenAI function definitions (Tier 2 tools marked `[REQUIRES CONFIRMATION]` in descriptions)
- **Frontend**: `apps/web-vue/src/components/AiAssistant.vue` — chat panel with FAB toggle
- **Store**: `apps/web-vue/src/stores/ai.js` — Pinia store with SSE reader

### Configuration

Set these in `apps/api/.env`:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

## Architecture

```
Browser (Vue 3)         AI Client (Claude Code, etc.)
     |                         |
     | HTTP                    | MCP (JSON-RPC over stdio)
     v                         v
┌─────────────────────────────────────────────┐
│              FastAPI Server                 │
│  ┌──────────────┐  ┌────────────────────┐  │
│  │ REST Routes  │  │ MCP Server (SSE)   │  │
│  └──────┬───────┘  └─────────┬──────────┘  │
│         │                    │              │
│         v                    v              │
│  ┌──────────────────────────────────────┐  │
│  │     Registry (shared tool store)     │  │
│  │  - contextvars user context          │  │
│  │  - audit logging (mcp.audit)         │  │
│  │  - Tier 2 propose/confirm           │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## Testing

```bash
# All MCP tests (195 unit + integration + AI)
python -m pytest packages/mcp/tests packages/mcp/servers/tests packages/ai/tests -v

# Stdio e2e tests (launches subprocess, tests JSON-RPC)
python -m pytest packages/mcp/tests/test_stdio_e2e.py -v
```

## New MCP Server Pattern

To add a new MCP server:

1. Create `packages/mcp/servers/<domain>_mcp.py`
2. Define `_svc` variables using `CrudService(CrudRepository(...))`
3. Define handler functions (one per tool)
4. Define `register_tools()` — register each tool with `Tool(name, description, input_schema)`
5. Define `main()` — calls `register_tools()` then `run_stdio(McpServer(...))`
6. Write tests in `packages/mcp/servers/tests/`
7. Wire into `apps/api/main.py` — import and call `register_tools()`
8. Add entry to `opencode.json`
