# MCP Tasks — Nova ERP: Dual REST API + MCP

> Consolidated from `docs/tasksv2.md` → `docs/tasksv3.md`. All phases complete.
>
> **204 backend tests + 5 e2e tests, all passing.**

---

## Phase 1 — Foundation Layer (`packages/mcp/`)

- [x] **1.1** Create `packages/mcp/` package:
  - `__init__.py`, `server.py`, `stdio.py`, `sse.py`, `router.py`, `types.py`, `registry.py`
- [x] **1.2** Wire `/mcp` SSE endpoint into `apps/api/main.py`
- [x] **1.3** Add `mcp` dependency in `apps/api/requirements.txt`
- [x] **1.4** Unit tests for all transport modes (stdio, SSE, server, registry)
- [x] **1.5** Audit current REST controllers/services for tenant scoping
  - **Finding:** No tenant scoping exists in any layer. Most business tables lack `business_id`. Documented in `AGENTS.md`.
- [x] **1.6** Shared auth/tenant-context resolver via `contextvars` in `registry.py`
  - `get_current_user()` returns authenticated user dict
  - Threaded through: router → sse → server → registry → AI service
- [x] **1.7** Audit logging hook in `registry.call_tool()` — logs tool, user, tenant, status, latency_ms to `mcp.audit` logger
- [x] **1.8** Tier classification documented: 72 Tier 1 (direct) + 5 Tier 2 (propose/confirm) tools

---

## Phase 2 — Core MCP Tools

- [x] **2.1** `database_mcp` — `list_tables`, `describe_table`, `execute_read_query` (SELECT-only, statement_timeout), resource `nova://schema`
- [x] **2.2** `inventory_mcp`
  - Read: `list_products`, `get_product`, `check_stock`, `search_products`, `list_categories`, `list_warehouses`, `list_uoms`, `list_brands`
  - Write: `create_product` (T1), `update_product` (T1), `delete_product` (T2)
  - Resources: `nova://inventory/products`, `nova://inventory/stock`
- [x] **2.3** `sales_mcp`
  - Read: `list_orders`, `get_order`, `list_customers`, `get_customer_aging`, `list_quotations`, `list_deliveries`, `list_price_lists`, `list_tax_rates`
  - Write: `create_order` (T1), `update_order_status` (T1), `confirm_order` (T2), `cancel_order` (T2), `convert_quotation_to_order` (T2)
  - Resources: `nova://sales/orders`, `nova://sales/customers`
- [x] **2.4** Register all servers in SSE router via `apps/api/main.py`
- [x] **2.5** Stdio mode functional — validated via e2e tests (`test_stdio_e2e.py`)
- [x] **2.6** Cross-tenant context tests in `test_registry.py` — verifies user context threading and contextvar isolation

---

## Phase 3 — Remaining Domain Tools

- [x] **3.1** `purchasing_mcp` — `list_purchase_orders`, `get_purchase_order`, `list_purchase_returns`, `list_rfqs`
- [x] **3.2** `accounting_mcp` — `list_chart_of_accounts`, `list_invoices`, `get_invoice`, `list_payments`, `list_payment_terms` (read-only)
- [x] **3.3** `admin_mcp` — `list_users`, `get_audit_log`, `list_settings`, `get_setting`, `list_notifications`, `list_scheduled_tasks`, `list_modules`
- [x] **3.4** `warehouse_mcp` — `list_goods_receipts`, `list_serial_numbers`, `list_batch_numbers`, `list_pick_lists`
- [x] **3.5** `hr_mcp` — `list_employees`, `get_employee`, `list_departments`, `list_attendance`, `list_leave_requests`, `list_payroll_entries`, `list_shifts`, `list_job_openings`
- [x] **3.6** `bi_mcp` — `list_kpis`, `get_kpi_values`, `list_dashboards`, `get_dashboard_widgets`
- [x] **3.7** `crm_mcp` — `list_leads`, `list_opportunities`, `list_suppliers`, `list_customer_groups`
- [x] **3.8** `projects_mcp` — `list_projects`, `get_project`, `list_tasks`, `list_milestones`
- [x] **3.9** `manufacturing_mcp` — `list_manufacturing_orders`, `list_boms`, `list_qc_inspections`, `list_shop_jobs`
- [x] **3.10** `maintenance_mcp` — `list_assets`, `list_maintenance_schedules`, `list_work_orders`
- [x] **3.11** `notifications_mcp` — `list_user_notifications`, `mark_notification_read`, `mark_all_notifications_read`
- [x] **3.12** All servers registered in SSE router via `apps/api/main.py`
- [x] **3.13** Tier 2 propose/confirm mechanism
  - `propose_action(tool_name, args)` → `{action_id, preview, tool}` (no execution)
  - `confirm_action(action_id)` executes pending handler
  - `confirm_action` registered as MCP tool for LLM calling
  - Pending actions expire after 5 minutes
- [x] **3.14** Integration tests for all namespaces (43 tests in `test_integration.py`)

---

## Phase 4 — In-App AI Assistant

- [x] **4.1** `apps/web-vue/src/components/AiAssistant.vue` — chat panel with FAB toggle, confirmation UI, prompt templates
- [x] **4.2** `apps/web-vue/src/stores/ai.js` — Pinia store with SSE stream reader, `pendingConfirmation` state handling
- [x] **4.3** `POST /api/ai/chat` — SSE streaming endpoint: user message → LLM (gpt-4o) → MCP tool execution → SSE response. User context forwarded from JWT via `contextvars`.
- [x] **4.4** AI Assistant toggle integrated in `AppLayout.vue`
- [x] **4.5** Prompt templates — clickable chips: "Recent products", "Order count", "Customers", "Stock check"
- [x] **4.6** Confirmation UI — shows action preview + Confirm/Cancel buttons when Tier 2 tool proposed. Emits `confirmation_required` SSE event.
- [x] **4.7** Rate limiting — `/api/ai/` classified as `'ai'` category (10 requests/second)

---

## Phase 5 — Developer Experience & Integration

- [x] **5.1** Register MCP servers in `opencode.json` (all 14 servers with DB env vars)
- [x] **5.2** `scripts/run-mcp-server.py` — CLI launcher for any MCP server
- [x] **5.3** `AGENTS.md` documents all 77 MCP tools with descriptions, Tier 1/Tier 2 classification, and user context access patterns
- [x] **5.4** e2e tests (5 tests in `test_stdio_e2e.py`): initialize/ping, tools/list, tool call error, Tier 2 propose/confirm cycle, Tier 2 unknown tool error
- [x] **5.5** `.env.example` updated with `OPENAI_API_KEY`, `OPENAI_MODEL`, `NOVA_TENANT_ID`, `NOVA_API_KEY`
- [x] **5.6** `AGENTS.md` with full MCP architecture, auth/context, Tier 1/Tier 2 classification, audit logging, propose/confirm flow, and testing instructions

---

## Key Files

| File | Purpose |
|------|---------|
| `packages/mcp/` (new) | MCP package: base server, stdio/SSE transports, tool registry, types, auth context, audit logging, propose/confirm |
| `packages/mcp/servers/*.py` (new, 14 files) | One module server per ERP domain (database, inventory, sales, purchasing, accounting, admin, warehouse, hr, bi, crm, projects, manufacturing, maintenance, notifications) |
| `packages/ai/` (new) | AI assistant: SSE-streaming chat service, FastAPI router, OpenAI function-calling integration |
| `apps/api/main.py` | MCP SSE router + AI router wired in; existing REST routers untouched |
| `packages/rate_limit/middleware.py` | Rate limit classes including `'ai'` (10 req/s) |
| `apps/web-vue/src/components/AiAssistant.vue` (new) | Chat panel with FAB toggle, confirmation UI, prompt templates |
| `apps/web-vue/src/stores/ai.js` (new) | Pinia store with SSE reader, pending confirmation state |
| `scripts/run-mcp-server.py` (new) | CLI launcher for any MCP server |
| `opencode.json` | MCP server registration for AI coding assistants |
| `AGENTS.md` | Full MCP architecture, tool classification, usage docs |

**Unchanged:** All existing controllers, services, repositories, Vue views, database schema, Docker config, deployment files.
