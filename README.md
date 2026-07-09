# Nova ERP

**Open-source ERP for food & beverage distribution.**

Inventory management, sales orders, warehouse pick lists, purchasing, accounting, and CRM — all in one system.

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3.11+ · FastAPI · psycopg2 · JWT auth |
| Frontend | Vue 3 · Vite · Pinia · Vue Router |
| Database | PostgreSQL 16+ |
| Deployment | Docker Compose |

## Quick Start

```bash
# 1. Database
createdb nova_erp
psql -d nova_erp -f database/schema.sql

# 2. Backend (port 8070)
cd apps/api
pip install -r requirements.txt
cp .env.example .env   # edit credentials
python main.py

# 3. Frontend (port 5173, proxies /api → 8070)
cd apps/web-vue
npm install
npm run dev
```

Open `http://localhost:5173`. Login with admin credentials.

### Docker Compose

```bash
npm run build  # in apps/web-vue first
docker compose up -d
# → http://localhost:8070
```

## Project Structure

```
├── apps/
│   ├── api/             # FastAPI backend (main.py, requirements.txt)
│   └── web-vue/         # Vue 3 SPA frontend
├── modules/             # Backend feature modules
│   ├── accounting/      # Invoices, payments, chart of accounts
│   ├── administration/  # Users, roles, settings, notifications
│   ├── bi/              # Dashboards, KPIs, reports
│   ├── core/            # Base services, repositories, controllers
│   ├── crm/             # Customers, suppliers
│   ├── enterprise/      # Enterprise-level features
│   ├── hr/              # Departments, employees, payroll, attendance
│   ├── integrations/    # API keys, sync, external integrations
│   ├── inventory/       # Products, stock levels, movements, UOM
│   ├── maintenance/     # Equipment, work orders
│   ├── manufacturing/   # BOM, production orders, QC
│   ├── migration/       # CSV import API
│   ├── planning/        # Planning module
│   ├── projects/        # Projects, tasks
│   ├── purchasing/      # Purchase orders, requisitions
│   ├── quality/         # QC inspections
│   ├── sales/           # Sales orders, quotations, returns
│   ├── search/          # Global search
│   └── warehouse/       # Pick lists, stock transfers, stock takes
├── packages/            # Shared backend packages
│   ├── analytics/       # Analytics engine
│   ├── auth/            # JWT auth, login/refresh
│   ├── billing/         # Stripe billing integration
│   ├── cache/           # Cache-Control headers middleware
│   ├── database/        # Connection pool, base models
│   ├── integrations/    # Integration helpers
│   ├── localization/    # Locale detection
│   ├── notifications/   # Notification dispatch
│   ├── permissions/     # RBAC permissions
│   ├── rate_limit/      # Rate limiting middleware
│   ├── reporting/       # Report generation
│   ├── security/        # CSP + security headers middleware
│   ├── shared/          # Shared DTOs, helpers
│   ├── ui/              # UI component library
│   ├── workflow/        # Workflow engine
│   └── ws/              # WebSocket manager
├── database/
│   ├── schema.sql       # Master schema
│   └── migrations/      # Incremental SQL migrations
├── docs/
│   ├── product-roadmap.md  # Task tracking
│   └── prd.md              # Product requirements
└── .github/             # CI, issue templates
```

## Key Features

- **Products** — Catalog with SKU, pricing, categories, brands, stock tracking
- **Inventory** — Multi-warehouse stock levels, movements, low-stock alerts
- **Sales Orders** — Draft → Confirm → Pick → Ship → Deliver → Invoice flow
- **Pick Lists** — Auto-generated on order confirm, item-level picking
- **Accounting** — Invoices, payments (cash/check), customer aging
- **Customers & Suppliers** — Full CRM with balance tracking
- **Migration** — CSV import with preview and rollback
- **User Management** — Roles, permissions, audit log

## Roadmap

See [docs/product-roadmap.md](docs/product-roadmap.md) for current status (64/64 tasks).

## License

[AGPLv3](LICENSE) — Free to use, modify, and distribute. Contributions welcome.
