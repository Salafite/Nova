# Nova ERP — MCP & AI Architecture Guide

## Overview

Nova ERP serves two protocols side by side:

| Protocol | Audience | Purpose |
|----------|----------|---------|
| **REST API** (`/api/*`) | Vue 3 SPA | UI rendering, CRUD, auth |
| **MCP** (stdio/SSE) | AI agents | Natural language tool calling |

All 15 MCP server modules live under `packages/mcp/servers/`. Each module corresponds to an ERP domain and registers tools via the global registry (`packages/mcp/registry.py`).

## Full Module Map (63 sub-modules)

| Module | Sub-modules | Frontend | Backend (T-code) | MCP |
|--------|-------------|----------|-----------------|-----|
| **Foundation** (7) | Home, Dashboard, Products, Inventory, Warehouse, Batch Numbers, Serial Numbers | 16 views | T0001I–T0009I, T0024I, T0064I, T0105I, T0106I | inventory, warehouse |
| **Accounting** (7) | Chart of Accounts, Journal Entries, Invoices, Payments, Payment Terms, Payment Methods, Finance | 6 views | T0026I, T0027I, T0089I–T0091I, T0096I, T0097I | accounting |
| **CRM** (3) | Customers, Leads, Opportunities | 4 views | T0010I, T0011I, T0092I–T0095I, T0103I | crm |
| **Sales** (8) | Sales, Sales Orders, Quotations, Delivery, Sales Returns, Price Lists, Tax Rates, POS | 8 views | T0012I, T0013I, T0016I, T0017I, T0067I, T0068I, T0077I–T0080I, T0083I–T0086I | sales, pos |
| **Procurement** (6) | Suppliers, Purchasing, Purchase Requisitions, RFQs, Goods Receipt, Purchase Returns | 6 views | T0014I, T0015I, T0069I–T0082I, T0103I | purchasing, warehouse |
| **Administration** (10) | Admin, Module Manager, Settings, Notifications, Audit Log, Scheduled Tasks, Multi-Tenant, Workflow, Governance, Platform | 10 views | T0021I–T0023I, T0025I, T0059I–T0063I, T0098I–T0100I | admin, notifications |
| **HR** (6) | HRMS, Attendance, Leave, Payroll, Recruitment, Timesheets | 9 views | T0028I–T0040I | hr |
| **BI** (5) | BI Foundation, Executive Dashboards, Operational Analytics, Forecasting, AI & Insights | 5 views | T0052I–T0055I | bi |
| **Manufacturing** (3) | Manufacturing, Quality, Shopfloor | 4 views | T0018I–T0020I, T0065I, T0066I | manufacturing |
| **Planning** (2) | Planning, Resource Planning | 2 views | T0024I | — |
| **Mobile** (2) | Mobile Foundation, Mobile POS | — | — | — |
| **Integrations** (3) | E-commerce, Third-Party, API Platform | 3 views | T0056I–T0058I | — |
| **Service & Projects** (5) | Service, Projects, Maintenance, Contracts & SLAs, Documents | 8 views | T0041I–T0050I, T0063I | projects, maintenance |

**Total: 13 modules, 63 sub-modules, ~80 view files, ~90 T-code controllers, 15 MCP servers**

## MCP Server List

| Server | Module | Tools |
|--------|--------|-------|
| database | `packages.mcp.servers.database_mcp` | `list_tables`, `describe_table`, `execute_read_query` |
| inventory | `packages.mcp.servers.inventory_mcp` | `list_products`, `get_product`, `create_product`, `update_product`, `delete_product`, `search_products`, `check_stock`, `list_categories`, `list_warehouses`, `list_uoms`, `list_brands` |
| sales | `packages.mcp.servers.sales_mcp` | `list_orders`, `get_order`, `create_order`, `update_order_status`, `confirm_order`, `cancel_order`, `list_customers`, `get_customer_aging`, `list_quotations`, `convert_quotation_to_order`, `list_deliveries`, `list_price_lists`, `list_tax_rates` |
| purchasing | `packages.mcp.servers.purchasing_mcp` | `list_purchase_orders`, `get_purchase_order`, `list_purchase_returns`, `list_rfqs`, `calculate_restock_forecast`, `propose_draft_purchase_order` |
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

### Multi-Tenant Isolation & Business Context Architecture

Multi-tenant data isolation is fully implemented and enforced end-to-end across database, API, and MCP layers:

1. **Database Schema & Foreign Keys**:
   - All business entity tables (`t0001` through `t0107`, excluding the platform table `t0059`) include `business_id INT REFERENCES "Nova".t0059(id)`.
   - Single-column indexes (`idx_tXXXX_business_id`) and composite indexes (`idx_tXXXX_business_id_id ON "Nova".tXXXX(business_id, id)`) guarantee fast, indexed tenant-filtered queries.
   - Pydantic models inherit `TenantMixin` (`business_id: Optional[int]`), and the model factory (`crud_model`) defaults to `tenant=True`.

2. **Context Propagation (`modules.core.context`)**:
   - Thread-safe and async-safe context variable `_current_tenant` managed via `get_current_tenant()`, `set_current_tenant()`, `reset_current_tenant()`, `clear_current_tenant()`, and `tenant_context()` context manager.

3. **JWT Authentication & Context Extraction**:
   - Access and refresh tokens embed `business_id` in claims during login, signup, and token refresh (`packages.auth.jwt`, `packages.auth.service`).
   - FastAPI dependency `get_current_user` in `packages.auth.deps` automatically extracts `business_id` from validated JWT tokens and sets the `current_tenant` context variable for the duration of the request.

4. **Repository & Service Layer Tenant Scoping**:
   - `CrudRepository` (`modules.core.repositories.base`) automatically injects `business_id = %s` on `list`, `get`, `update`, `delete`, and `count` operations.
   - Auto-injects `business_id` from the active tenant context on `create()`.
   - Protects against tenant spoofing on `update()` (ignores or rejects attempts to mutate `business_id`).
   - Provides `get_unscoped()` for ownership checks and platform administration.
   - `CrudService` (`modules.core.services.base`) and domain services strictly honor active tenant context.

5. **Cross-Tenant Access Protection & Security Auditing**:
   - Base controllers (`modules.core.controllers.base`) and custom routes verify record ownership via `check_record_ownership()`.
   - Cross-tenant access attempts return `HTTP 403 Forbidden` and log a security audit event to table `t0023` and `security.audit` logger (`packages.security.audit.record_security_event`).

6. **MCP Server & AI Tool Isolation**:
   - **SSE Transport**: Sessions validate JWT via `Depends(get_current_user)` and inherit the authenticated user's `business_id`.
   - **Stdio Transport**: Initializes tenant context from `NOVA_TENANT_ID` environment variable or user dict.
   - **In-App AI Assistant**: `POST /api/ai/chat` forwards authenticated user and tenant context to every MCP tool execution and Tier 2 propose/confirm action.
   - **Audit Logging**: Every MCP tool call is recorded in `mcp.audit` with `tool`, `user`, `tenant`, `status`, and `latency_ms`.

### Audit Logging

Every MCP tool call is logged via `packages/mcp/registry.call_tool()` with:
- `tool`, `user`, `tenant`, `status` (success/error), `latency_ms`
- Log output goes to the `mcp.audit` logger (configure via standard logging)

## Tool Safety Tiers

All 79 MCP tools are classified into two tiers:

| Tier | Policy | Count | Examples |
|------|--------|-------|---------|
| **Tier 1** | Direct execution (audit-logged) | 73 | All `list_*`, `get_*`, `check_*`, `search_*`, `create_*`, `update_*`, `calculate_restock_forecast`, `mark_notification_read` |
| **Tier 2** | Requires propose/confirm | 6 | `delete_product`, `confirm_order`, `cancel_order`, `convert_quotation_to_order`, `propose_draft_purchase_order`, `mark_all_notifications_read` |

**Tier 2 behavior:** When the AI assistant calls a Tier 2 tool, it routes through `propose_action()` which returns an `action_id` and preview instead of executing. The UI shows the preview and requires user confirmation before `confirm_action(action_id)` executes the operation.

### Tier 2 Tools

| Tool | Server | Risk |
|------|--------|------|
| `delete_product` | inventory | Irreversible deletion |
| `confirm_order` | sales | Reserves stock, financial impact |
| `cancel_order` | sales | Releases stock, financial impact |
| `convert_quotation_to_order` | sales | Irreversible status change |
| `propose_draft_purchase_order` | purchasing | Financial commitment/PO draft creation |
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
