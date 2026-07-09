# MCP Plan — Nova ERP: Dual REST API + MCP Architecture

> Consolidated from `docs/planv2.md` → `docs/planv3.md`. All phases complete.

## 1. Vision

Nova ERP serves two audiences through two parallel protocols — **REST APIs** for the web UI and **MCP servers** for AI assistants — both backed by the same business logic and database.

| Protocol | Audience | Purpose |
|----------|----------|---------|
| **REST API** (`/api/*`) | Vue 3 SPA (browser) | UI rendering, CRUD operations, auth, file uploads |
| **MCP** (stdio / SSE) | AI agents (Claude Code, Cursor, in-app AI) | Natural language tool calling, data querying, automation |

Both are first-class citizens. Neither replaces the other.

**Core constraint:** every MCP tool call runs in the same tenant + permission context as the REST request that would have done the same thing. Nova is multi-tenant. If the MCP layer doesn't inherit that isolation, it becomes the easiest way to accidentally leak data across tenants.

---

## 2. Architecture

```
┌─────────────────────────────────┐   ┌─────────────────────────────┐
│       Browser (Vue 3 SPA)       │   │   AI Client (Claude Code,   │
│  ┌───────────────────────────┐  │   │   Cursor, in-app AI, etc.)  │
│  │ Axios → REST via HTTP     │  │   │  ┌────────────────────────┐ │
│  └──────────┬────────────────┘  │   │  │ MCP Client → JSON-RPC  │ │
└─────────────┼───────────────────┘   │  └───────────┬────────────┘ │
              │ HTTP                  └──────────────┼──────────────┘
              ▼                                      │
┌───────────────────────────────────────────────────────────────────┐
│                  FastAPI Server (port 8070)                       │
│                                                                   │
│  ┌──────────────────────────────┐  ┌────────────────────────────┐ │
│  │     REST Controllers         │  │     MCP Server(s)          │ │
│  └──────────┬────────────────────┘  └────────────┬──────────────┘ │
│             │                                    │                │
│             ▼                                    ▼                │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Shared Auth/Tenant Context Middleware                      │  │
│  │  Resolves: tenant_id, user_id, role, permission set         │  │
│  │  Injected into every REST request AND every MCP tool call   │  │
│  └───────────────────────────┬─────────────────────────────────┘  │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │             Service Layer (shared)                          │  │
│  │    CrudService + Custom Services per module                 │  │
│  │    All queries scoped by tenant_id at this layer,           │  │
│  │    not left to callers to remember                          │  │
│  └───────────────────────────┬─────────────────────────────────┘  │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │           Repository Layer (shared)                         │  │
│  │    CrudRepository — raw SQL via psycopg2                    │  │
│  └───────────────────────────┬─────────────────────────────────┘  │
└──────────────────────────────┼────────────────────────────────────┘
                               ▼
                     ┌──────────────────────┐
                     │   PostgreSQL 16      │
                     │   (Nova schema)      │
                     └──────────────────────┘
```

**Key principle:** REST controllers and MCP tools call the same `CrudService` / `CrudRepository` methods. No business logic duplication.

**Key principle:** Tenant scoping and permission checks live in the service layer, not in REST controllers or MCP tool handlers individually. This means whichever protocol calls in, isolation is enforced once, centrally.

---

## 3. REST API — What Stays

Unchanged. Auth, 100+ CRUD endpoints, custom endpoints, billing, BI, WebSocket.

---

## 4. MCP — What Gets Added

### 4.1 MCP Transports

| Transport | For | Protocol |
|-----------|-----|----------|
| **stdio** | External AI agents (Claude Code, Cursor) | JSON-RPC over stdin/stdout |
| **SSE** | In-app AI assistant (browser user) | JSON-RPC over Server-Sent Events at `/mcp` |

**Auth per transport:**
- **stdio** — runs as a specific service account / API key tied to one tenant + role, set via env var at process launch (`NOVA_TENANT_ID`, `NOVA_API_KEY`).
- **SSE** — inherits the logged-in user's session (same JWT/cookie the REST API already validates), automatically scoped to whatever that user is already allowed to see and do.

### 4.2 MCP Servers

All 14 servers co-exist in the same process, with tools *namespaced* by domain. Each server registers tools via the global registry.

| Domain | Module | Example Tools |
|--------|--------|---------------|
| `database` | `packages.mcp.servers.database_mcp` | `list_tables`, `describe_table`, `execute_read_query` |
| `inventory` | `packages.mcp.servers.inventory_mcp` | `list_products`, `get_product`, `create_product`, `update_product`, `delete_product`, `search_products`, `check_stock`, `list_categories`, `list_warehouses`, `list_uoms`, `list_brands` |
| `sales` | `packages.mcp.servers.sales_mcp` | `list_orders`, `get_order`, `create_order`, `update_order_status`, `confirm_order`, `cancel_order`, `list_customers`, `get_customer_aging`, `list_quotations`, `convert_quotation_to_order`, `list_deliveries`, `list_price_lists`, `list_tax_rates` |
| `purchasing` | `packages.mcp.servers.purchasing_mcp` | `list_purchase_orders`, `get_purchase_order`, `list_purchase_returns`, `list_rfqs` |
| `accounting` | `packages.mcp.servers.accounting_mcp` | `list_chart_of_accounts`, `list_invoices`, `get_invoice`, `list_payments`, `list_payment_terms` |
| `admin` | `packages.mcp.servers.admin_mcp` | `list_users`, `get_audit_log`, `list_settings`, `get_setting`, `list_notifications`, `list_scheduled_tasks`, `list_modules` |
| `warehouse` | `packages.mcp.servers.warehouse_mcp` | `list_goods_receipts`, `list_serial_numbers`, `list_batch_numbers`, `list_pick_lists` |
| `hr` | `packages.mcp.servers.hr_mcp` | `list_employees`, `get_employee`, `list_departments`, `list_attendance`, `list_leave_requests`, `list_payroll_entries`, `list_shifts`, `list_job_openings` |
| `bi` | `packages.mcp.servers.bi_mcp` | `list_kpis`, `get_kpi_values`, `list_dashboards`, `get_dashboard_widgets` |
| `crm` | `packages.mcp.servers.crm_mcp` | `list_leads`, `list_opportunities`, `list_suppliers`, `list_customer_groups` |
| `projects` | `packages.mcp.servers.projects_mcp` | `list_projects`, `get_project`, `list_tasks`, `list_milestones` |
| `manufacturing` | `packages.mcp.servers.manufacturing_mcp` | `list_manufacturing_orders`, `list_boms`, `list_qc_inspections`, `list_shop_jobs` |
| `maintenance` | `packages.mcp.servers.maintenance_mcp` | `list_assets`, `list_maintenance_schedules`, `list_work_orders` |
| `notifications` | `packages.mcp.servers.notifications_mcp` | `list_user_notifications`, `mark_notification_read`, `mark_all_notifications_read` |

### 4.3 MCP Exposures

Tools, Resources, and Prompts — all three MCP primitives are used.

### 4.4 Write-Operation Guardrails (Tier 1 / Tier 2)

Read tools (`list_*`, `get_*`, `check_stock`, aging reports) are low-risk — exposed freely.

Write tools need one more layer than REST does, because the caller isn't a person clicking a button that reflects their own confirmed intent — it's an LLM interpreting natural language and deciding to call a tool.

| Tier | Policy | Count | Examples |
|------|--------|-------|---------|
| **Tier 1** | Direct execution (audit-logged) | 72 | All `list_*`, `get_*`, `check_*`, `search_*`, `create_*`, `update_*`, `mark_notification_read` |
| **Tier 2** | Requires propose/confirm | 5 | `delete_product`, `confirm_order`, `cancel_order`, `convert_quotation_to_order`, `mark_all_notifications_read` |

**Tier 2 flow:** `propose_action(tool, args)` → `{action_id, preview}` (no execution). UI shows preview + confirm/cancel. User confirms → `confirm_action(action_id)` executes.

`execute_read_query` specifically: constrained to SELECT-only with a Postgres role, query timeout (5s), and row limit (500 rows).

### 4.5 REST ↔ MCP Parity

Every CRUD REST endpoint has an MCP tool equivalent, same underlying service call.

---

## 5. Observability

Every MCP tool call logs: tool, user (or service account), tenant, result status, latency. Logged via `mcp.audit` logger.

---

## 6. Implementation Summary

### Phase 1 — Foundation
- `packages/mcp/` — base server class, stdio + SSE transports, tool registry
- `/mcp` SSE endpoint wired into FastAPI
- Shared auth/tenant-context middleware via `contextvars` — `get_current_user()` available to all tool handlers
- Audit logging hook in the tool registry

### Phase 2 — Core Tools
- `database_mcp`, `inventory_mcp`, `sales_mcp` built with read tools first, then Tier 1/2 writes
- SSE router registration, e2e tests
- Cross-tenant context tests

### Phase 3 — Remaining Domain Tools
- purchasing, accounting, admin, warehouse, hr, bi, crm, projects, manufacturing, maintenance, notifications
- Integration tests (43 tests)
- Tier 2 propose/confirm mechanism with 5-minute TTL

### Phase 4 — In-App AI Assistant
- Vue 3 chat panel (AiAssistant.vue), Pinia store (ai.js)
- `POST /api/ai/chat` SSE streaming endpoint → LLM (gpt-4o) → MCP tool execution
- Confirmation UI for Tier 2 actions
- Rate limiting (10 req/s) on `/api/ai/chat`

### Phase 5 — DX & Polish
- `opencode.json` server registration
- `scripts/run-mcp-server.py` CLI launcher
- `AGENTS.md` documentation with Tier 1/2 classification, auth context, architecture diagram
- e2e tests (5 tests including Tier 2 propose/confirm cycle)

---

## 7. Dependencies

```
mcp>=1.0.0
pydantic>=2.0.0
httpx>=0.27.0
```

---

## 8. Guarantees

- Zero changes to existing REST controllers, services, or repositories
- Zero changes to the Vue 3 frontend (except new AI Assistant component)
- Zero changes to database schema or migrations
- Zero changes to Dockerfile, docker-compose, or deployment config

---

## 9. Known Gaps (Pre-Existing, Deferred)

**Tenant scoping:** No tenant scoping currently exists in any layer (controllers, services, or repositories). Most business tables lack a `business_id` column. Full tenant isolation requires:
1. Adding `business_id` to all business tables (schema migration)
2. Injecting tenant context in the service/repository layer
3. Adding `business_id` to the JWT payload for efficiency

Without this, MCP tools operate against all data regardless of tenant.
