# Nova ERP — Task Register

## Legend

| Icon | Meaning |
|------|---------|
| ✅ | Done |
| 🔨 | In progress |
| ⬜ | Not started |
| ❌ | Broken / blocked |

---

## 1. Cross-cutting Infrastructure

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1.1 | DB connection pool with `search_path="Nova"` + quoted schema | ✅ | `connection.py`, `base.py` |
| 1.2 | Auth system (JWT login, Bearer interceptor, 401 redirect) | ✅ | `auth.js`, `client.js` |
| 1.3 | Vue Router hash-based with auth guard | ✅ | `router/index.js` |
| 1.4 | AppLayout — dual mode (sidebar 240px / grid topbar) | ✅ | `AppLayout.vue` |
| 1.5 | Nav store — loads from `/NavigationData.json`, fallback hardcoded | ✅ | `stores/nav.js` |
| 1.6 | Toast composable (module-scoped reactive) | ✅ | `composables/useToast.js` |
| 1.7 | i18n composable with `t()` + shared dict | ✅ | `composables/useI18n.js` |
| 1.8 | RTL auto-switch via `dir` on `<html>`, CSS overrides | ✅ | `useI18n.apply()`, `style.css` |
| 1.9 | Nav store — bilingual labels (`label_ar`, `section_ar`) | ✅ | `stores/nav.js` |
| 1.10 | AppSidebar / AppLayout — locale-aware nav labels | ✅ | `AppSidebar.vue`, `AppLayout.vue` |
| 1.11 | Auto-discovery of controllers (`modules/*/controllers/__init__.py`) | ✅ | Core init |
| 1.12 | Windows process management (taskkill, Start-Process) | ✅ | Operational |

---

## 2. Backend — Clean Architecture Audit

Every controller must follow: `controller (thin) → service (logic) → repository (SQL) → models (Pydantic)`.

### 2.1 Inventory Module

| Code | Controller | Service | Repository | DB Table | Status | Notes |
|------|-----------|---------|------------|----------|--------|-------|
| T0001 | `T0001I.py` | `CrudService` (generic) | `CrudRepository` | `T0001` | ✅ | UOM — 7 rows |
| T0002 | `T0002I.py` | `CrudService` (generic) | `CrudRepository` | `T0002` | ✅ | UOM Conversions — Vue screen built |
| T0003 | `T0003I.py` | `CrudService` (generic) | `CrudRepository` | `T0003` | ✅ | Products — 6 rows |
| T0004 | `T0004I.py` | `CrudService` (generic) | `CrudRepository` | `T0004` | ✅ | Barcodes — Vue screen built |
| T0005 | `T0005I.py` | `CrudService` (generic) | `CrudRepository` | `T0005` | ✅ | Attributes — Vue screen built |
| T0006 | `T0006I.py` | `CrudService` (generic) | `CrudRepository` | `T0006` | ✅ | Attr Values |
| T0007 | `T0007I.py` | `CrudService` (generic) | `CrudRepository` | `T0007` | ✅ | Product UOM |
| T0008 | `T0008I.py` | `CrudService` (generic) | `CrudRepository` | `T0008` | ✅ | Warehouses — new controller + Vue screen |
| T0009 | `T0009I.py` | `CrudService` (generic) | `CrudRepository` | `T0009` | ✅ | Stock Levels — new controller + rebuilt InventoryView |

### 2.2 CRM Module

| Code | Controller | Service | Repository | DB Table | Status | Notes |
|------|-----------|---------|------------|----------|--------|-------|
| T0010 | `T0010I.py` | `CustomerService` | `CrudRepository` | `T0010` | ✅ | Fixed — added default_price_list_id, default_tax_rate_id, payment_term_id columns + T0083/T0085 tables |
| T0011 | `T0011I.py` | `CrudService` (generic) | `CrudRepository` | `T0011` | ✅ | Suppliers — 3 rows, Vue screen rebuilt |
| T0012 | `T0012I.py` | `SalesOrderService` | `CrudRepository` | `T0012` | ✅ | Sales Orders (in modules/sales/), Vue screen rebuilt |
| T0013 | `T0013I.py` | `SalesLineService` | `CrudRepository` | `T0013` | ✅ | Sales Order Lines (in modules/sales/) |
| T0014 | `T0014I.py` | `PurchaseOrderService` | `CrudRepository` | `T0014` | ✅ | Purchase Orders (in modules/purchasing/), Vue screen rebuilt |
| T0015 | `T0015I.py` | `PurchaseLineService` | `CrudRepository` | `T0015` | ✅ | Purchase Order Lines (in modules/purchasing/) |
| T0016 | `T0016I.py` | `InstallmentPlanService` | `CrudRepository` | `T0016` | ✅ | Installment Plans (in modules/sales/) |
| T0017 | `T0017I.py` | `CrudService` (generic) | `CrudRepository` | `T0017` | ✅ | Install Payments (in modules/sales/) |
| T0018 | `T0018I.py` | `MfgOrderService` | `CrudRepository` | `T0018` | ✅ | Manufacturing Orders (in modules/manufacturing/) |
| T0019 | `T0019I.py` | `CrudService` (generic) | `CrudRepository` | `T0019` | ✅ | QC Inspections (in modules/manufacturing/) |
| T0020 | `T0020I.py` | `CrudService` (generic) | `CrudRepository` | `T0020` | ✅ | Shop Floor Jobs (in modules/manufacturing/) |

### 2.3 Administration Module

| Code | Controller | Service | Repository | DB Table | Status | Notes |
|------|-----------|---------|------------|----------|--------|-------|
| T0021 | `T0021I.py` | `UserService` | `CrudRepository` | `T0021` | ✅ | Users — Vue screen rebuilt with full CRUD + i18n |
| T0022 | `T0022I.py` | `CrudService` | `CrudRepository` | `T0022` | ✅ | Nav Permissions (Roles) |
| T0023 | `T0023I.py` | `CrudService` | `CrudRepository` | `T0023` | ✅ | Audit Log |
| T0024 | `T0024I.py` | `CrudService` | `CrudRepository` | `T0024` | ✅ | Planning module (not admin) — exists at `modules/planning/`, API 200 |
| T0025 | `T0025I.py` | `SettingService` | `CrudRepository` | `T0025` | ✅ | Settings — refactored, works |
| T0098 | `T0098I.py` | `NotificationService` | `CrudRepository` | `T0098` | ✅ | User Notifications — NotificationsView exists |
| T0099 | `T0099I.py` | `SchedulerService` | `CrudRepository` | `T0099` | ✅ | Scheduled Tasks |
| T0100 | `T0100I.py` | `ModuleService` | `CrudRepository` | `T0100` | ✅ | Fixed — `dependencies` Optional in response model |

### 2.4 Accounting Module

| Code | Controller | Service | Repository | DB Table | Status | Notes |
|------|-----------|---------|------------|----------|--------|-------|
| T0026 | `T0026I.py` | `CrudService` | `CrudRepository` | `T0026` | ✅ | Chart of Accounts — Vue screen built |
| T0027 | `T0027I.py` | `JournalEntryService` | `CrudRepository` | `T0027` | ✅ | Journal Entries |
| T0090 | `T0090I.py` | `CrudService` (generic) | `CrudRepository` | `T0090` | ✅ | Fixed — table created via migration |
| T0091 | `T0091I.py` | `CrudService` (generic) | `CrudRepository` | `T0091` | ✅ | Payments |
| T0096 | `T0096I.py` | `CrudService` (generic) | `CrudRepository` | `T0096` | ✅ | Payment Terms — Vue screen built |
| T0097 | `T0097I.py` | `CrudService` (generic) | `CrudRepository` | `T0097` | ✅ | Payment Methods — Vue screen built |

### 2.5 All Modules — Controller Audit (DB live)

All 99 of 100 possible controllers exist and return 200 OK. Only T0089 (Journal Entry Lines) is intentionally absent — it's a child table managed through T0027.

| Range | Module dir(s) | Controllers | Status | Notes |
|-------|--------------|-------------|--------|-------|
| T0001–T0009 | `inventory/`, `warehouse/` | 11 | ✅ All 200 | T0008 appears in both inventory and warehouse (duplicate) |
| T0010–T0011 | `crm/` | 2 | ✅ All 200 | Customers, Suppliers |
| T0012–T0013, T0016–T0017 | `sales/` | 5 | ✅ All 200 | Sales Orders (T0012 with custom SalesOrderService), lines, installments |
| T0014–T0015 | `purchasing/` | 2 | ✅ All 200 | Purchase Orders, lines (both custom services) |
| T0018–T0020 | `manufacturing/` | 3 | ✅ All 200 | MFG Orders (T0018 custom MfgOrderService), QC, shop floor |
| T0021–T0025, T0098–T0100 | `administration/` | 8 | ✅ All 200 | Users, Nav, Audit, Settings, Notifications, Scheduler, Modules |
| T0026–T0027, T0090–T0091, T0096–T0097 | `accounting/` | 6 | ✅ All 200 | COA, Journal Entries, Invoices, Payments, Payment Terms, Methods |
| T0028–T0040 | `hr/` | 13 | ✅ All 200 | Depts, Designations, Employees, Contracts, Docs, Shifts, Attendance, Leave, Payroll, Jobs, Candidates |
| T0041–T0043 | `maintenance/` | 3 | ✅ All 200 | Maintenance equipment, work orders |
| T0044–T0050 | `projects/` | 7 | ✅ All 200 | Projects, tasks |
| T0056–T0058 | `integrations/` | 3 | ✅ All 200 | API keys, integrations, sync logs |
| T0064 | `inventory/` | 1 | ✅ 200 | Stock Movements |
| T0065–T0066 | `manufacturing/` | 2 | ✅ All 200 | BOM, work centers |
| T0067–T0068 | `sales/` | 2 | ✅ All 200 | Quotations, returns |
| T0069–T0074 | `purchasing/` | 6 | ✅ All 200 | Requisitions, approvals (custom services) |
| T0075–T0076 | `warehouse/` | 2 | ✅ All 200 | Stock takes, transfers (custom services) |
| T0077–T0080 | `sales/` | 4 | ✅ All 200 | Invoicing, billing (custom services) |
| T0081–T0082 | `purchasing/` | 2 | ✅ All 200 | Goods receipt, supplier returns (custom) |
| T0083–T0086 | `sales/` | 4 | ✅ All 200 | Price lists, discounts (custom services) |
| T0087–T0088 | `warehouse/` | 2 | ✅ All 200 | Inventory adjustments (custom services) |
| T0092–T0095 | `crm/` | 4 | ✅ All 200 | CRM analytics, campaigns (custom services) |
| T0089 | — | 0 | N/A | Intentionally absent — child of T0027, managed through journal entry |

### 2.6 Backend Fixes — Status

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.6.1 | Fix T0010I (Customers) 500 error | ✅ | FIXED: Added missing FK columns (default_price_list_id, default_tax_rate_id, payment_term_id) + created T0083 (Price Lists) and T0085 (Tax Rates) tables |
| 2.6.2 | Fix T0090I (Invoices) 500 error | ✅ | FIXED: Table created via migration at `database/migrations/001_full_schema.sql` |
| 2.6.3 | Audit all `T*I.py` for correct `business_columns` | ✅ | 99 controllers audited, 5 issues found and FIXED (see 2.6.3a below) |
| 2.6.4 | Add dedicated services for T0002–T0009 | ✅ | Deferred (YAGNI) — all 8 are pure data CRUD with no domain logic; generic CrudService is correct until business rules emerge |
| 2.6.5 | Verify all DB tables exist per controller | ✅ | Cross-referenced all controllers vs `packages/database/schema.sql` — all tables defined. Migration created at `database/migrations/001_full_schema.sql`. |

#### 2.6.3a — business_columns fixes applied

| Controller | Table | Issue | Fix |
|-----------|-------|-------|-----|
| `crm/T0010I.py` | T0010 | Missing `default_price_list_id`, `default_tax_rate_id`, `payment_term_id` | Added 3 FK columns |
| `accounting/T0026I.py` | T0026 | Missing `parent_id` for hierarchy | Added parent_id |
| `purchasing/T0069I.py` | T0069 | Missing `description` field | Added description |
| `integrations/T0058I.py` | T0058 | Extra `is_active` (column doesn't exist in schema; table has `status` instead) | Replaced with correct columns |
| `administration/T0098I.py` | T0098 | Extra `created_at` (audit column, auto-managed) | Removed |

#### 2.6.5a — T0100 schema gap fixed

T0100 (Module Registry) had a controller but no schema definition in `packages/database/schema.sql`. It was only in `database/schema.sql`. The comprehensive migration at `database/migrations/001_full_schema.sql` now includes T0100 with `IF NOT EXISTS`.

#### 2.6.5b — Comprehensive migration created

`database/migrations/001_full_schema.sql` — complete schema with `IF NOT EXISTS` for all core tables (T0001–T0100) in the `"Nova"` schema with enums, indexes, and FK constraints.

`scripts/init_db.py` — Python script that:
1. Creates `"Nova"` schema
2. Runs migration SQL
3. Seeds bcrypt-hashed user passwords (admin/admin123, sales/sales123, viewer/viewer123)
4. Seeds navigation items

**To initialize the database:**
```
# Requires PostgreSQL running on localhost:5432, database "Stage" existing
python scripts/init_db.py
```

---

## 3. Frontend — Vue Screens

### 3.1 Screens with Real Backend (build priority)

| # | Route | View | Backend | Status | Notes |
|---|-------|------|---------|--------|-------|
| 3.1.1 | `#/` | `HomeView.vue` | Multiple APIs | ✅ | Rebuilt — i18n, live stats, app grid |
| 3.1.2 | `#/settings` | `SettingsView.vue` | T0025I | ✅ | i18n labels done |
| 3.1.3 | `#/uom` | `UOMView.vue` | T0001I | ✅ | CRUD + i18n |
| 3.1.4 | `#/products` | `ProductsView.vue` | T0003I | ✅ | CRUD + i18n |
| 3.1.5 | `#/modules` | `ModuleManagerView.vue` | T0100I | ✅ | Scan/install/toggle + i18n |

### 3.2 Placeholder Screens (need rebuild)

These exist but are basic placeholders — need full CRUD + i18n.

| # | Route | View | Backend | Status | Priority |
|---|-------|------|---------|--------|----------|
| 3.2.1 | `#/dashboard` | `DashboardView.vue` | Aggregates (8 endpoints) | ✅ | Rebuilt — live stats + recent activity |
| 3.2.2 | `#/customers` | `CustomersView.vue` | T0010I ✅ | ✅ | High — full CRUD + i18n rebuilt |
| 3.2.3 | `#/suppliers` | `SuppliersView.vue` | T0011I ✅ | ✅ | High — full CRUD + i18n rebuilt |
| 3.2.4 | `#/sales` | `SalesView.vue` | T0012I ✅ | ✅ | High — full CRUD + i18n rebuilt |
| 3.2.5 | `#/purchasing` | `PurchasingView.vue` | T0014I ✅ | ✅ | High — full CRUD + i18n rebuilt |
| 3.2.6 | `#/inventory` | `InventoryView.vue` | T0009I | ✅ | Rebuilt — real stock levels from T0009 |
| 3.2.7 | `#/warehouse` | `WarehouseView.vue` → redirects to `#/warehouses` | T0008I ✅ | ✅ | Redirects to full CRUD + i18n WarehousesView |
| 3.2.8 | `#/finance` | `FinanceView.vue` | T0090I ✅ | ✅ | Rebuilt — full CRUD + i18n |
| 3.2.9 | `#/admin` | `AdminView.vue` | T0021I | ✅ | Medium — full CRUD + i18n rebuilt |

### 3.3 New Screens to Build (inventory module first)

| # | Route | View | Backend | Status | Priority |
|---|-------|------|---------|--------|----------|
| 3.3.1 | `#/uom-conversions` | `UOMConvView.vue` | T0002I | ✅ | High |
| 3.3.2 | `#/barcodes` | `BarcodesView.vue` | T0004I | ✅ | Medium |
| 3.3.3 | `#/attributes` | `AttributesView.vue` | T0005I | ✅ | Medium |
| 3.3.4 | `#/stock-movements` | `StockMovementsView.vue` | T0064I | ✅ | Medium |
| 3.3.5 | `#/warehouses` | `WarehouseView.vue` | T0008I | ✅ | High |

### 3.4 New Screens (Accounting & HR)

| # | Route | View | Backend | Status | Priority |
|---|-------|------|---------|--------|----------|
| 3.4.1 | `#/chart-of-accounts` | `ChartOfAccountsView.vue` | T0026I ✅ | ✅ | High |
| 3.4.2 | `#/payment-terms` | `PaymentTermsView.vue` | T0096I ✅ | ✅ | Medium |
| 3.4.3 | `#/payment-methods` | `PaymentMethodsView.vue` | T0097I ✅ | ✅ | Medium |
| 3.4.4 | `#/departments` | `DepartmentsView.vue` | T0028I ✅ | ✅ | Medium |
| 3.4.5 | `#/journal-entries` | `JournalEntriesView.vue` | T0027I ✅ | ✅ | High |
| 3.4.6 | `#/payments` | `PaymentsView.vue` | T0091I ✅ | ✅ | Medium |
| 3.4.7 | `#/designations` | `DesignationsView.vue` | T0029I ✅ | ✅ | Medium |
| 3.4.8 | `#/employees` | `EmployeesView.vue` | T0030I ✅ | ✅ | High |

### 3.5 Frontend Fixes / Polish

| # | Task | Status | Notes |
|---|------|--------|-------|
| 3.4.1 | LoginView i18n | ✅ | `t()` for all labels, `:dir="dir"` on root |
| 3.4.2 | DashboardView i18n + real data | ✅ | Live stats from 8 endpoints |
| 3.4.3 | All remaining placeholder screens get i18n | ✅ | 3.2 all rebuilt with full i18n |
| 3.4.4 | AppTopBar page title i18n | ✅ | Uses `label_ar` via `AppLayout.pageTitle`; Logout button uses `t()` |
| 3.4.5 | RTL polish: sidebar collapse arrow | ✅ | Shows `chevron_right` in RTL |
| 3.4.6 | RTL polish: toast position | ✅ | `left: 16px` in RTL |
| 3.4.7 | RTL polish: data-table text-align | ✅ | th/td default `text-align: right` in RTL |
| 3.4.8 | Add `dir` attribute to root element of every screen | ✅ | All 27 screens now have `:dir="dir"` |
| 3.4.9 | Replace all `confirm()` with proper modal | ✅ | `ConfirmDialog.vue` — 12 screens updated |

---

## 4. Infrastructure & DevOps

| # | Task | Status | Notes |
|---|------|--------|-------|
| 4.1 | Create `schema.sql` with all Nova tables | ✅ | Consolidated into `database/schema.sql` — all 100 tables (T0001–T0100) |
| 4.2 | Migration script for missing tables | ✅ | `database/migrations/002_missing_tables.sql` — 61 tables added, now 100/100 in DB |
| 4.3 | Health endpoint with DB connectivity check | ✅ | `/api/health` |
| 4.4 | API documentation (Swagger/OpenAPI) | ✅ | FastAPI auto-generates at `/docs` (title: "Nova ERP API", v1.0) |
| 4.5 | Server restart script (one command) | ✅ | `scripts/restart_server.ps1` — kills + restarts on port 8070 |
| 4.6 | Build + deploy script (frontend) | ✅ | `scripts/deploy.ps1` — builds frontend + restarts server |
| 4.7 | Git init + .gitignore | ✅ | `.gitignore` enhanced, `.gitattributes` added, `git init` done |

---

## 5. i18n Translation Dictionary

Keys currently in `locales/en.json`:

```
loading, no-records, no-data, no-modules, scan-hint,
edit, delete, cancel, save, saving, add-new, confirm-delete,
retry, actions, status, active, inactive, disabled,
search, close, new, total, name, category, price, sku,
code, version, description, module, install, installed,
uninstall, enable, disable, yes, no, base-unit, deleting,
welcome, select-app,
failed-load, failed-save, saved-ok,
settings, search-settings, unsaved-changes, unsaved,
save-all, save-group, reset-value,
module-manager, module-sub, scan-modules, available,
installed-modules, available-modules, controllers,
module-installed, module-uninstalled, module-enabled,
module-disabled, install-failed, uninstall-failed,
toggle-failed,
uom-title, uom-sub, new-uom, edit-uom,
uom-conv-title, uom-conv-sub, new-uom-conv, edit-uom-conv, conv-factor,
barcodes-title, barcodes-sub, new-barcode, edit-barcode, barcode-type, barcode-primary,
attr-title, attr-sub, new-attr, edit-attr, attr-type, attr-required, attr-sort,
stock-move-title, stock-move-sub, new-movement, edit-movement, stock-move-type,
stock-qty-change, stock-balance, stock-move-ref, stock-move-ref-id, date,
warehouse-title, warehouse-sub, new-warehouse, edit-warehouse, warehouse-location,
customers-title, customers-sub, new-customer, edit-customer, customer-group,
customer-phone, customer-email, customer-credit, customer-balance,
suppliers-title, suppliers-sub, new-supplier, edit-supplier,
supplier-phone, supplier-email, supplier-payment-terms, supplier-rating,
sales-title, sales-sub, new-sales-order, edit-sales-order, sales-order-number,
sales-customer, sales-subtotal, sales-tax, sales-grand-total, sales-order-date, sales-notes,
purchasing-title, purchasing-sub, new-purchase-order, edit-purchase-order,
purchase-order-number, purchase-supplier, purchase-total, purchase-order-date,
purchase-expected-date, purchase-notes,
admin-title, admin-sub, admin-username, admin-full-name, admin-email, admin-role,
admin-password, admin-last-login, admin-delete-confirm, new-user, edit-user,
coa-title, coa-sub, new-account, edit-account, coa-code, coa-name, coa-type,
coa-currency, coa-delete-confirm,
payterm-title, payterm-sub, new-payterm, edit-payterm, payterm-due-days,
payterm-discount, payterm-discount-days, payterm-default, payterm-delete-confirm,
paymethod-title, paymethod-sub, new-paymethod, edit-paymethod,
paymethod-default, paymethod-delete-confirm,
invoices-title, invoices-sub, new-invoice, edit-invoice, invoices-number,
invoices-type, invoices-partner, invoices-issue-date, invoices-due-date,
invoices-total, invoices-delete-confirm,
dept-title, dept-sub, new-dept, edit-dept, dept-code, dept-name, dept-parent,
dept-manager, dept-delete-confirm,
je-title, je-sub, new-je, edit-je, je-date, je-reference, je-delete-confirm,
payments-title, payments-sub, new-payment, edit-payment, payment-date,
payment-invoice, payment-partner, payment-method, payment-amount,
payment-reference, payment-delete-confirm,
desig-title, desig-sub, new-desig, edit-desig, desig-code, desig-name,
desig-department, desig-delete-confirm,
emp-title, emp-sub, new-emp, edit-emp, emp-code, emp-name, emp-arabic-name,
emp-email, emp-phone, emp-address, emp-national-id, emp-passport, emp-gender,
emp-marital, emp-birth-date, emp-hire-date, emp-term-date,
emp-employment-status, emp-department, emp-designation, emp-manager,
emp-delete-confirm
```

**Missing keys to add** (when building each screen):
- `screen-title`, `screen-sub` for each new screen
- All field labels (code, name, status, actions are already covered)
- All modal/form labels (Cancel, Save, Delete confirmed)
- All toast messages
- EmployeesView, DesignationsView, etc. (HR screens not yet built)

---

## Summary

| Area | Done | In Progress | Not Started | Broken |
|------|------|-------------|-------------|--------|
| Infrastructure | 18 | 0 | 0 | 0 |
| Backend controllers | 99/99 | 0 | 0 | 0 |
| Vue screens (real) | 24 | 0 | 1 | 0 |
| Vue screens (placeholder) | 5 | 0 | 4 | 0 |
| i18n translation | ~230 keys | 0 | ~40+ keys | 0 |
| RTL polish | Basic | 0 | 5 | 0 |
