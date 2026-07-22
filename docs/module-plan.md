# Nova ERP — Module Implementation Plan

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Implemented |
| 🟡 | Partial |
| ❌ | Not implemented |
| N/A | Not applicable |

---

## 1. Foundation (7 sub-modules)

| Sub-module | Frontend View | Route | Backend T-Code(s) | MCP Server | Priority |
|---|---|---|---|---|---|
| Home | ✅ `views/home/HomeView.vue` | `/` | — | — | — |
| Dashboard | ✅ `views/dashboard/DashboardView.vue` | `/dashboard` | — | — | — |
| Products | ✅ `views/products/ProductsView.vue` | `/products` | T0001I–T0007I | inventory_mcp | — |
| Inventory | ✅ `views/inventory/InventoryView.vue` | `/inventory` | T0064I | inventory_mcp | — |
| Warehouse | ✅ `views/warehouses/WarehouseView.vue` | `/warehouses` | T0008I, T0009I | warehouse_mcp | — |
| Batch Numbers | ❌ `views/batch-numbers/BatchNumbersView.vue` | `/inventory/batch-numbers` | T0105I | warehouse_mcp | **High** |
| Serial Numbers | ❌ `views/serial-numbers/SerialNumbersView.vue` | `/inventory/serial-numbers` | T0106I | warehouse_mcp | **High** |

## 2. Accounting (7 sub-modules)

| Sub-module | Frontend | Route | Backend | MCP | Priority |
|---|---|---|---|---|---|
| Chart of Accounts | ✅ `views/chart-of-accounts/ChartOfAccountsView.vue` | `/chart-of-accounts` | T0026I | accounting_mcp | — |
| Journal Entries | ✅ `views/journal-entries/JournalEntriesView.vue` | `/journal-entries` | T0027I | accounting_mcp | — |
| Invoices | ✅ `views/finance/FinanceView.vue` | `/finance` | T0089I–T0091I | accounting_mcp | — |
| Payments | ✅ `views/payments/PaymentsView.vue` | `/payments` | T0096I, T0097I | accounting_mcp | — |
| Payment Terms | ✅ `views/payment-terms/PaymentTermsView.vue` | `/payment-terms` | T???? | accounting_mcp | — |
| Payment Methods | ✅ `views/payment-methods/PaymentMethodsView.vue` | `/payment-methods` | T???? | accounting_mcp | — |
| Finance | ✅ (same as Invoices) | `/finance` | — | — | — |

## 3. CRM (3 sub-modules)

| Sub-module | Frontend | Route | Backend | MCP | Priority |
|---|---|---|---|---|---|
| Customers | ✅ `views/customers/*.vue` | `/customers` | T0010I, T0011I | crm_mcp | — |
| Leads | ❌ `views/crm/LeadsView.vue` | `/crm/leads` | T0092I, T0093I | crm_mcp | **High** |
| Opportunities | ❌ `views/crm/OpportunitiesView.vue` | `/crm/opportunities` | T0094I, T0095I | crm_mcp | **High** |

## 4. Sales (8 sub-modules)

| Sub-module | Frontend | Route | Backend | MCP | Priority |
|---|---|---|---|---|---|
| Sales | ✅ `views/sales/SalesView.vue` | `/sales` | T0012I, T0013I | sales_mcp | — |
| Sales Orders | ✅ (same as Sales) | `/sales` | — | — | — |
| Quotations | ✅ `views/sales/QuotationsView.vue` | `/sales/quotations` | T0016I, T0017I | sales_mcp | — |
| Delivery | ✅ `views/sales/DeliveriesView.vue` | `/sales/deliveries` | T0067I, T0068I | sales_mcp | — |
| Sales Returns | ✅ `views/sales/SalesReturnsView.vue` | `/sales/returns` | T0077I–T0080I | sales_mcp | — |
| Price Lists | ✅ `views/sales/PriceListsView.vue` | `/sales/price-lists` | T0083I, T0084I | sales_mcp | — |
| Tax Rates | ✅ `views/sales/TaxRatesView.vue` | `/sales/tax-rates` | T0085I, T0086I | sales_mcp | — |
| POS | ✅ `views/pos/POSView.vue` | `/pos` | (checkout) | pos_mcp | — |

## 5. Procurement (6 sub-modules)

| Sub-module | Frontend | Route | Backend | MCP | Priority |
|---|---|---|---|---|---|
| Suppliers | ✅ `views/suppliers/SuppliersView.vue` | `/suppliers` | T0103I | crm_mcp | — |
| Purchasing | ✅ `views/purchasing/PurchasingView.vue` | `/purchasing` | T0014I, T0015I | purchasing_mcp | — |
| Purchase Requisitions | ✅ `views/purchasing/PurchaseRequisitionsView.vue` | `/purchasing/requisitions` | T0069I, T0070I | purchasing_mcp | — |
| RFQs | ✅ `views/purchasing/RFQView.vue` | `/purchasing/rfqs` | T0071I–T0074I | purchasing_mcp | — |
| Goods Receipt | ❌ `views/purchasing/GoodsReceiptView.vue` | `/purchasing/goods-receipt` | T0075I, T0076I (warehouse) | warehouse_mcp | **High** |
| Purchase Returns | ✅ `views/purchasing/PurchaseReturnsView.vue` | `/purchasing/returns` | T0081I, T0082I | purchasing_mcp | — |

## 6. Administration (10 sub-modules)

| Sub-module | Frontend | Route | Backend | MCP | Priority |
|---|---|---|---|---|---|
| Admin | ✅ `views/admin/AdminView.vue` | `/admin` | T0021I–T0023I | admin_mcp | — |
| Module Manager | ✅ `views/admin/ModuleManagerView.vue` | `/modules` | T0099I | admin_mcp | — |
| Settings | ✅ `views/settings/SettingsView.vue` | `/settings` | T0025I | admin_mcp | — |
| Notifications | ✅ `views/notifications/NotificationsView.vue` | `/notifications` | T0098I | notifications_mcp | — |
| Audit Log | ❌ `views/admin/AuditLogView.vue` | `/admin/audit-log` | — | admin_mcp | **Medium** |
| Scheduled Tasks | ❌ `views/admin/ScheduledTasksView.vue` | `/admin/scheduled-tasks` | T0100I | admin_mcp | **Medium** |
| Multi-Tenant Arch | ❌ → Enterprise | — | T0059I–T0063I | — | Low |
| Workflow Automation | ❌ `views/admin/WorkflowView.vue` | `/admin/workflow` | T0061I (enterprise) | — | **Medium** |
| Enterprise Governance | ❌ `views/admin/GovernanceView.vue` | `/admin/governance` | T0062I, T0063I | — | Low |
| Enterprise Platform | ❌ `views/admin/PlatformView.vue` | `/admin/platform` | — | — | Low |

## 7. HR (6 sub-modules)

| Sub-module | Frontend | Route | Backend | MCP | Priority |
|---|---|---|---|---|---|
| HRMS Foundation | ✅ `views/employees/*` | `/employees` | T0028I–T0040I | hr_mcp | — |
| Attendance & Time | ✅ `views/hr/AttendanceView.vue` | `/hr/attendance` | T0032I, T0033I | hr_mcp | — |
| Leave Management | ✅ `views/hr/LeaveRequestsView.vue` | `/hr/leaves` | T0034I, T0035I | hr_mcp | — |
| Payroll Management | ✅ `views/hr/PayrollView.vue` | `/hr/payroll` | T0036I–T0038I | hr_mcp | — |
| Recruitment & Onbrd | ✅ `views/hr/JobOpeningsView.vue` | `/hr/jobs` | T0039I, T0040I | hr_mcp | — |
| Timesheets | ❌ `views/hr/TimesheetsView.vue` | `/hr/timesheets` | — | — | **Medium** |

## 8. BI (5 sub-modules)

| Sub-module | Frontend | Route | Backend | MCP | Priority |
|---|---|---|---|---|---|
| BI Foundation | ✅ (via KPIs/Dashboards) | — | T0052I–T0055I | bi_mcp | — |
| Executive Dashboards | ✅ `views/bi/DashboardBuilderView.vue` | `/bi/dashboards` | (dashboard_service) | bi_mcp | — |
| Operational Analytics | 🟡 via Reports | `/bi/reports` | — | bi_mcp | **Medium** |
| Forecasting | ❌ `views/bi/ForecastingView.vue` | `/bi/forecasting` | — | — | **Medium** |
| AI & Insights | 🟡 via AI Assistant | `/ai` | (packages/ai) | — | **Medium** |

## 9. Manufacturing (3 sub-modules)

| Sub-module | Frontend | Route | Backend | MCP | Priority |
|---|---|---|---|---|---|
| Manufacturing | 🟡 `views/manufacturing/*` | — | T0018I–T0020I | manufacturing_mcp | — |
| Quality | ✅ `views/manufacturing/QCInspectionView.vue` | `/manufacturing/qc` | T0065I, T0066I | manufacturing_mcp | — |
| Shopfloor | ❌ `views/manufacturing/ShopfloorView.vue` | `/manufacturing/shopfloor` | — | — | **Medium** |

## 10. Planning (2 sub-modules)

| Sub-module | Frontend | Route | Backend | MCP | Priority |
|---|---|---|---|---|---|
| Planning | ✅ `views/planning/ProductionPlansView.vue` | `/planning` | T0024I | — | — |
| Resource Planning | ❌ `views/planning/ResourcePlanningView.vue` | `/planning/resources` | — | — | **Medium** |

## 11. Mobile (2 sub-modules)

| Sub-module | Frontend | Route | Backend | MCP | Priority |
|---|---|---|---|---|---|
| Mobile Foundation | ❌ `apps/mobile/` | — | — | — | Low |
| Mobile POS | ❌ (empty dir) | — | — | — | Low |

## 12. Integrations (3 sub-modules)

| Sub-module | Frontend | Route | Backend | MCP | Priority |
|---|---|---|---|---|---|
| E-commerce Integration | ❌ `views/integrations/EcommerceView.vue` | `/integrations/ecommerce` | T0056I | — | **Medium** |
| Third-Party Integrations | ❌ `views/integrations/IntegrationsView.vue` | `/integrations` | T0057I | — | **Medium** |
| Public API Platform | ❌ `views/integrations/ApiPlatformView.vue` | `/integrations/api` | T0058I | — | **Medium** |

## 13. Service & Projects (5 sub-modules)

| Sub-module | Frontend | Route | Backend | MCP | Priority |
|---|---|---|---|---|---|
| Service Management | ❌ `views/service/ServiceView.vue` | `/service` | — | — | **Medium** |
| Project Management | ❌ `views/projects/ProjectsView.vue` | `/projects` | T0044I–T0050I | projects_mcp | **High** |
| Maintenance Management | ❌ `views/maintenance/*` | `/maintenance` | T0041I–T0043I | maintenance_mcp | **High** |
| Contracts & SLAs | ❌ `views/projects/ContractsView.vue` | `/projects/contracts` | — | — | **Medium** |
| Document Management | ❌ `views/projects/DocumentsView.vue` | `/projects/documents` | — | — | Low |

---

## Summary

| Status | Count |
|--------|-------|
| ✅ Implemented | ~40 |
| 🟡 Partial | ~4 |
| ❌ Missing (High) | 8 |
| ❌ Missing (Medium) | 10 |
| ❌ Missing (Low) | ~6 |
| **Total sub-modules** | **63** |

## Implementation Queue

### Phase 1 — High Priority (has backend support)
1. Batch Numbers & Serial Numbers (T0105I, T0106I exist)
2. Leads & Opportunities (T0092I–T0095I exist)
3. Goods Receipt (T0075I, T0076I exist)
4. Project Management (T0044I–T0050I exist)
5. Maintenance Management (T0041I–T0043I exist)

### Phase 2 — Medium Priority (partial or no backend)
6. Audit Log, Scheduled Tasks
7. Workflow Automation
8. Timesheets
9. Forecasting, AI Insights
10. Shopfloor
11. Resource Planning
12. Integrations (Ecommerce, Third-Party, API)

### Phase 3 — Low Priority
13. Enterprise (Multi-Tenant, Governance, Platform)
14. Mobile (Foundation, Mobile POS)
15. Document Management
