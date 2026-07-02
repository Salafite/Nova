# PRD — Nova

## 1. Overview

### Product Summary
Nova is an open-source ERP for small F&B distributors (5–50M/month revenue) that replaces legacy systems with real-time inventory, automated order-to-cash flows, and a single source of truth across sales, warehouse, and accounting. Built on Nuxt 3 + FastAPI + PostgreSQL, deployable on-prem (Podman) or cloud.

### Objective
This PRD covers the MVP (4–8 week build): the end-to-end order-to-cash flow that proves the concept with Makka as the first customer. The MVP includes user auth with role management, product catalog with phantom product detection, real-time inventory, order management with stock reservation, pick list generation, accounts receivable with multi-payment tracking, supplier management, and a legacy migration tool.

### Market Differentiation
Nova is vertical-first (F&B distribution) rather than a generic ERP requiring customization. The founder built Makka's legacy C# system 10 years ago — no competitor can offer a migration path from that codebase. Open-core pricing ($5/user/month) undercuts Odoo and ERPNext at small scale.

### Magic Moment
A salesman places an order → inventory is reserved in real time → the warehouse receives a correct pick list → the accountant sees the receivable created. All within seconds instead of hours of manual handoffs.

The technical implementation must deliver:
- Real-time data propagation (sub-second) across all roles
- Inventory accuracy through phantom product cleanup on migration
- Role-specific views: salesman sees catalog + stock, warehouse sees pick lists, accountant sees receivables

### Success Criteria
- Time from order placement to receivable creation: < 30 seconds (p95)
- Orders placed without warehouse phone call check: > 90% within 30 days post-launch
- Pick list accuracy: > 99%
- Page load < 2s on 3G, API response < 200ms (p95)
- All P0 features functional with test coverage
- Migration from legacy C# system completes without data loss

## 2. Technical Architecture

### Architecture Overview

```mermaid
graph TB
    Client[Nuxt 3 PWA] -->|HTTP/WebSocket| API[FastAPI Backend]
    API -->|SQLAlchemy| DB[(PostgreSQL)]
    API -->|Auth0 SDK| Auth[Auth0]
    API -->|Stripe SDK| Payments[Stripe]
    Client -->|PostHog SDK| Analytics[PostHog]
    API -->|Resend SDK| Email[Resend]
    API -->|Sentry SDK| Errors[Sentry]

    subgraph Deployment
        direction LR
        Cloud[Cloud Host] --- OnPrem[On-Prem Podman]
    end

    API --> Deployment
    DB --> Deployment
```

### Chosen Stack

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | Nuxt 3 | Vue framework with SSR, file-based routing, module ecosystem. Hybrid rendering (SSR for public pages, SPA for app behind login). |
| Backend | FastAPI | Modern Python async framework, type-hint-driven validation, auto OpenAPI docs. Natural for Python-native team. |
| Database | PostgreSQL | Right choice for ERP with complex relational data (products, orders, inventory, payments). Mature, ACID-compliant. |
| Auth | Auth0 | Enterprise-ready, works with Python backend, social login and MFA out of the box. Multi-tenant support via organizations. |
| Payments | Stripe | Flexible subscription billing for $5/user/month model. Checkout, customer portal, webhooks. |
| Analytics | PostHog | Free tier (1M events/month). Session replay and feature flags bundled. |
| Email | Resend | Transactional email for account management, notifications, receipts. Developer-friendly API. |
| Error tracking | Sentry | Crash and performance monitoring. SDKs for Nuxt and Python/ASGI. |

### Stack Integration Guide

**Setup order:**
1. PostgreSQL (local dev) → schema with Alembic migrations
2. Auth0 tenant → application + API + roles
3. FastAPI project with SQLAlchemy + Alembic + Auth0 middleware
4. Nuxt 3 project with auth module, PostHog plugin, Sentry module
5. Stripe account → products + prices + webhook endpoint
6. Resend domain verification → transactional email templates
7. Environment variables wired to `.env` for all secrets
8. Docker Compose for local development with all services
9. Podman Compose for on-prem deployment packaging

**Integration patterns:**
- FastAPI uses `python-jose` for Auth0 JWT validation middleware
- Nuxt 3 uses `@nuxtjs/auth-next` or direct Auth0 SDK for client-side auth
- Stripe webhooks handled via FastAPI route with signature verification
- Real-time updates via WebSocket (FastAPI's native WebSocket support) for inventory/order status changes
- Alembic for schema migrations; `asyncpg` for async PostgreSQL driver
- PostHog: `posthog` Python SDK on backend, `posthog-js` on Nuxt client
- Sentry: `sentry-sdk` with FastAPI/ASGI integration, `@nuxtjs/sentry` module

**Required environment variables:**
```
# Auth0
AUTH0_DOMAIN=
AUTH0_API_AUDIENCE=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/nova

# Stripe
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_ID_MONTHLY=

# Resend
RESEND_API_KEY=

# PostHog
POSTHOG_API_KEY=
POSTHOG_HOST=

# Sentry
SENTRY_DSN=

# App
NOVA_ENV=development|staging|production
NOVA_INSTANCE_TYPE=cloud|on_prem
```

### Repository Structure

```
nova/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── products.py
│   │   │   │   ├── inventory.py
│   │   │   │   ├── orders.py
│   │   │   │   ├── warehouse.py
│   │   │   │   ├── accounting.py
│   │   │   │   ├── suppliers.py
│   │   │   │   └── migration.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── database.py
│   │   ├── models/
│   │   │   ├── product.py
│   │   │   ├── inventory.py
│   │   │   ├── order.py
│   │   │   ├── pick_list.py
│   │   │   ├── receivable.py
│   │   │   ├── customer.py
│   │   │   └── supplier.py
│   │   ├── schemas/
│   │   │   ├── product.py
│   │   │   ├── order.py
│   │   │   └── ...
│   │   ├── services/
│   │   │   ├── inventory.py
│   │   │   ├── order_flow.py
│   │   │   └── migration.py
│   │   ├── ws/
│   │   │   └── handlers.py
│   │   └── main.py
│   ├── migrations/
│   │   └── versions/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── pages/
│   │   ├── index.vue
│   │   ├── login.vue
│   │   ├── dashboard.vue
│   │   ├── products/
│   │   ├── orders/
│   │   ├── warehouse/
│   │   └── accounting/
│   ├── components/
│   │   ├── ui/
│   │   └── features/
│   ├── composables/
│   ├── plugins/
│   ├── middleware/
│   ├── nuxt.config.ts
│   ├── package.json
│   └── Dockerfile
├── docker/
│   ├── docker-compose.yml
│   └── podman-compose.yml
├── .env.example
├── README.md
└── LICENSE
```

### Infrastructure & Deployment

**Development:**
- Docker Compose with FastAPI, PostgreSQL, and Nuxt in separate containers
- Hot reload for both frontend and backend
- Local Postgres with persistent volume

**Cloud (staging/production):**
- FastAPI: Railway, Render, or Fly.io
- PostgreSQL: Neon (serverless, generous free tier, scale-to-zero)
- Nuxt: Vercel or Cloudflare Pages
- Auth0: SaaS (managed)
- Stripe: SaaS (managed)
- PostHog: Cloud (managed, free tier)

**On-prem (production):**
- Podman Compose with all services in containers
- PostgreSQL as a container with persistent volume
- Environment variable driven configuration
- Health checks and restart policies for reliability

**CI/CD:**
- GitHub Actions for linting, tests, and build
- Docker image pushed to registry
- Cloud deploy: trigger via GitHub Actions
- On-prem deploy: pull image on server, run podman-compose up

### Security Considerations

- Auth0 JWT validation on every API request (middleware in FastAPI)
- Role-based access control: salesman, warehouse, accountant, admin
- Stripe webhook signature verification
- Input validation via FastAPI/Pydantic schemas
- CORS configured for frontend origin only
- Rate limiting on auth endpoints (FastAPI middleware)
- SQL injection prevention via SQLAlchemy parameterized queries
- Sentry configured to scrub PII from error payloads — no tokens, passwords, or personal data in breadcrumbs
- HTTPS enforced in production
- Secrets via environment variables, not checked into version control
- Podman rootless mode for on-prem deployments

### Cost Estimate

**First 6 months at low scale (< 100 users):**

| Service | Monthly Cost | Free Tier Details |
|---|---|---|
| Auth0 | $0 | Free tier: up to 7,000 MAUs |
| Stripe | $0 + 2.9%/transaction | Pay-as-you-go |
| Neon Postgres | $0 | Free tier: 0.5GB storage, 100hr compute/month |
| Railway/Render | $0–$7 | Free tier: limited hours/bandwidth |
| Vercel | $0 | Free tier: 100GB bandwidth, 6000 build mins |
| PostHog | $0 | Free: 1M events/month |
| Resend | $0 | Free: 3,000 emails/month |
| Sentry | $0 | Free: 5K errors/month |
| **Total** | **$0–$7** | All within free tiers at launch scale |

## 3. Data Model

### Entity Definitions

**Using SQLAlchemy models with asyncpg:**

```sql
-- users table (managed by Auth0, mirrored for role/org data)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth0_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'salesman',
    -- enum: salesman, warehouse, accountant, admin
    business_id UUID NOT NULL REFERENCES businesses(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- businesses (multi-tenant organization)
CREATE TABLE businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subscription_status VARCHAR(50) DEFAULT 'active',
    -- enum: active, trialing, past_due, canceled
    stripe_customer_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- categories
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- products (core catalog)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    category_id UUID REFERENCES categories(id),
    sku VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    unit_of_measure VARCHAR(50) NOT NULL DEFAULT 'piece',
    -- e.g., piece, kg, bag, liter
    unit_price DECIMAL(12,2) NOT NULL DEFAULT 0,
    low_stock_threshold INTEGER DEFAULT 10,
    is_phantom BOOLEAN DEFAULT FALSE,
    -- flagged if no transactions in 12+ months
    last_transaction_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- inventory (current stock per product)
CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id),
    business_id UUID NOT NULL REFERENCES businesses(id),
    quantity INTEGER NOT NULL DEFAULT 0,
    reserved_quantity INTEGER NOT NULL DEFAULT 0,
    available_quantity INTEGER GENERATED ALWAYS AS (quantity - reserved_quantity) STORED,
    warehouse_location VARCHAR(100),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- inventory_movements (audit trail)
CREATE TABLE inventory_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id),
    business_id UUID NOT NULL REFERENCES businesses(id),
    change_type VARCHAR(50) NOT NULL,
    -- enum: received, sold, adjusted, reserved, released, picked
    quantity_change INTEGER NOT NULL,
    reference_type VARCHAR(50),
    reference_id UUID,
    notes TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- customers
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    email VARCHAR(255),
    address TEXT,
    credit_limit DECIMAL(12,2) DEFAULT 0,
    balance DECIMAL(12,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- orders
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    salesman_id UUID NOT NULL REFERENCES users(id),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    -- enum: draft, confirmed, picking, picked, delivered, invoiced, cancelled
    notes TEXT,
    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- order_items
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    line_total DECIMAL(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    picked_quantity INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    -- enum: pending, picked, backordered, cancelled
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- pick_lists
CREATE TABLE pick_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id),
    business_id UUID NOT NULL REFERENCES businesses(id),
    warehouse_user_id UUID REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'pending',
    -- enum: pending, in_progress, completed, partially_completed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- pick_list_items
CREATE TABLE pick_list_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pick_list_id UUID NOT NULL REFERENCES pick_lists(id) ON DELETE CASCADE,
    order_item_id UUID NOT NULL REFERENCES order_items(id),
    product_id UUID NOT NULL REFERENCES products(id),
    expected_quantity INTEGER NOT NULL,
    picked_quantity INTEGER DEFAULT 0,
    warehouse_location VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    -- enum: pending, picked, backordered
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- receivables
CREATE TABLE receivables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    order_id UUID NOT NULL REFERENCES orders(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    amount DECIMAL(12,2) NOT NULL,
    paid_amount DECIMAL(12,2) DEFAULT 0,
    balance DECIMAL(12,2) GENERATED ALWAYS AS (amount - paid_amount) STORED,
    status VARCHAR(50) DEFAULT 'pending',
    -- enum: pending, partially_paid, paid, overdue, written_off
    due_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- payments
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receivable_id UUID NOT NULL REFERENCES receivables(id),
    business_id UUID NOT NULL REFERENCES businesses(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    payment_method VARCHAR(50) NOT NULL,
    -- enum: cash, check, installment, bank_transfer
    amount DECIMAL(12,2) NOT NULL,
    reference_number VARCHAR(255),
    -- check number, installment plan ID, or transaction ref
    payment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(50) DEFAULT 'completed',
    -- enum: pending, completed, failed, refunded
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- suppliers
CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    name VARCHAR(255) NOT NULL,
    contact_person VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(255),
    address TEXT,
    payment_terms VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- product_suppliers (many-to-many)
CREATE TABLE product_suppliers (
    product_id UUID NOT NULL REFERENCES products(id),
    supplier_id UUID NOT NULL REFERENCES suppliers(id),
    supplier_sku VARCHAR(100),
    unit_cost DECIMAL(12,2),
    lead_time_days INTEGER,
    PRIMARY KEY (product_id, supplier_id)
);
```

### Relationships

- **Business → Users:** 1:many (one business has many users)
- **Business → Products:** 1:many (one business has many products)
- **Product → Category:** many:1 (each product belongs to one category)
- **Product → Inventory:** 1:1 (each product has one inventory record)
- **Inventory → InventoryMovements:** 1:many (audit trail)
- **Order → Customer:** many:1
- **Order → OrderItems:** 1:many (cascade delete)
- **Order → PickList:** 1:1
- **PickList → PickListItems:** 1:many (cascade delete)
- **OrderItem → PickListItem:** 1:many
- **Order → Receivable:** 1:1
- **Receivable → Payments:** 1:many
- **Product → Suppliers:** many:many (via product_suppliers)
- **Customer → Receivables:** 1:many
- **Customer → Payments:** 1:many

### Indexes

| Table | Index | Reason |
|---|---|---|
| products | (business_id, sku) UNIQUE | Lookup by SKU per business |
| products | (business_id, is_phantom) | Filter phantom products per business |
| orders | (business_id, status) | Dashboard queries by status |
| orders | (business_id, salesman_id) | Salesman's order history |
| orders | (business_id, customer_id) | Customer order history |
| order_items | (order_id) | Load all items for an order |
| inventory | (product_id) UNIQUE | Fast stock lookup by product |
| inventory | (business_id) | Stock queries per business |
| inventory_movements | (product_id, created_at) | Stock movement history |
| pick_lists | (order_id) | Pick list lookup by order |
| pick_lists | (business_id, status) | Warehouse dashboard |
| receivables | (business_id, status) | Accounting dashboard |
| receivables | (customer_id) | Customer balance lookup |
| payments | (receivable_id) | All payments for a receivable |
| payments | (customer_id, payment_date) | Customer payment history |
| customers | (business_id) | Customer list per business |

## 4. API Specification

### API Design Philosophy

RESTful API with JSON responses. All endpoints require Auth0 JWT Bearer token via `Authorization` header. Business/tenant ID is inferred from the authenticated user's `business_id`. Errors return a consistent format:

```json
{
    "error": "error_code",
    "message": "Human-readable description",
    "details": []
}
```

Pagination uses cursor-based pagination with `limit` and `cursor` query parameters.

### Endpoints

**Auth** (managed by Auth0 SDK — app mirrors user data):

```
POST /api/v1/auth/callback — Auth0 post-login, creates/updates user record
GET    /api/v1/auth/me — Current user profile
```

**Products:**

```
GET    /api/v1/products — List products (query: ?is_phantom=true, ?category_id=, ?search=, ?limit=, ?cursor=)
POST   /api/v1/products — Create product
GET    /api/v1/products/{id} — Get product
PUT    /api/v1/products/{id} — Update product
DELETE /api/v1/products/{id} — Soft-delete (set is_active=false)
POST   /api/v1/products/scan-phantoms — Flag products with no transactions in 12+ months as phantom
```

**Categories:**

```
GET    /api/v1/categories — List categories
POST   /api/v1/categories — Create category
PUT    /api/v1/categories/{id} — Update category
DELETE /api/v1/categories/{id} — Delete category (only if no products linked)
```

**Inventory:**

```
GET    /api/v1/inventory — List inventory (query: ?low_stock=true, ?category=)
GET    /api/v1/inventory/{product_id} — Stock for a specific product
GET    /api/v1/inventory/{product_id}/movements — Movement history (query: ?from=, ?to=, ?limit=)
```

**Orders:**

```
GET    /api/v1/orders — List orders (query: ?status=, ?customer_id=, ?salesman_id=, ?from=, ?to=, ?limit=, ?cursor=)
POST   /api/v1/orders — Create order (reserves inventory)
GET    /api/v1/orders/{id} — Get order with items
POST   /api/v1/orders/{id}/confirm — Confirm order (reserves inventory)
POST   /api/v1/orders/{id}/cancel — Cancel order (releases inventory)
```

**Warehouse (Pick Lists):**

```
GET    /api/v1/pick-lists — List pick lists (query: ?status=)
GET    /api/v1/pick-lists/{id} — Get pick list with items
POST   /api/v1/pick-lists/{id}/start — Mark pick list as in_progress
POST   /api/v1/pick-lists/{id}/pick-item — Mark a pick list item as picked
POST   /api/v1/pick-lists/{id}/complete — Complete pick list (updates inventory)
POST   /api/v1/pick-lists/{id}/backorder — Mark item as backordered
```

**Customers:**

```
GET    /api/v1/customers — List customers
POST   /api/v1/customers — Create customer
GET    /api/v1/customers/{id} — Get customer with balance
PUT    /api/v1/customers/{id} — Update customer
GET    /api/v1/customers/{id}/balance — Customer balance across all payment methods
GET    /api/v1/customers/{id}/payments — Payment history for a customer
```

**Accounting (Receivables):**

```
GET    /api/v1/receivables — List receivables (query: ?status=, ?customer_id=, ?from=, ?to=)
GET    /api/v1/receivables/{id} — Get receivable with payments
POST   /api/v1/receivables/{id}/pay — Record a payment against a receivable
```

**Suppliers:**

```
GET    /api/v1/suppliers — List suppliers
POST   /api/v1/suppliers — Create supplier
GET    /api/v1/suppliers/{id} — Get supplier
PUT    /api/v1/suppliers/{id} — Update supplier
DELETE /api/v1/suppliers/{id} — Soft-delete
```

**Migration:**

```
POST   /api/v1/migration/upload-csv — Upload legacy data as CSV (products, customers, inventory, orders)
GET    /api/v1/migration/status — Check migration job status
POST   /api/v1/migration/preview — Preview imported data before committing
POST   /api/v1/migration/commit — Commit migration
POST   /api/v1/migration/rollback — Rollback last migration
```

**Dashboard:**

```
GET    /api/v1/dashboard/summary — Role-specific dashboard summary (salesman: open orders, low stock; warehouse: new picks; accountant: pending receivables)
```

**WebSocket:**

```
WS /ws/orders/{business_id} — Real-time order status updates (new orders, status changes)
WS /ws/inventory/{business_id} — Real-time inventory changes (stock levels, reservations)
```

## 5. User Stories

### Epic: Authentication & Onboarding

**US-001: Business sign-up**
As a business owner, I want to create an account and invite my team so that we can all use Nova.
Acceptance Criteria:
- [ ] Owner signs up via Auth0
- [ ] Business record is created
- [ ] Owner can invite users by email with role assignment
- [ ] Invited users receive email with sign-up link
- [ ] First login for invited user creates their user record

**US-002: Role-based access**
As an admin, I want users to have specific roles so that they only see relevant screens and data.
Acceptance Criteria:
- [ ] Roles: admin, salesman, warehouse, accountant
- [ ] Admin sees all screens
- [ ] Salesman sees orders, products, inventory (read), customers
- [ ] Warehouse sees pick lists, inventory (read)
- [ ] Accountant sees receivables, payments, customers (balance)

### Epic: Product Catalog

**US-003: Manage products**
As a salesman or admin, I want to add, edit, and search products so that the catalog reflects what we sell.
Acceptance Criteria:
- [ ] Create product with SKU, name, category, unit of measure, price, low stock threshold
- [ ] Edit product fields
- [ ] Soft-delete products (deactivate, not delete)
- [ ] Search by name, SKU, or category
- [ ] View product detail with current stock level

**US-004: Phantom product detection**
As an admin, I want to identify products with no recent transactions so that I can clean up the catalog.
Acceptance Criteria:
- [ ] System flags products with no orders in 12+ months as phantom
- [ ] Admin can review flagged products
- [ ] Admin can deactivate phantom products in bulk
- [ ] Phantom products don't appear in order catalog by default

### Epic: Inventory

**US-005: View real-time inventory**
As a salesman, I want to see current stock levels for every product so that I know what I can promise.
Acceptance Criteria:
- [ ] Product list shows available quantity (stock - reserved)
- [ ] Inventory updates in real time when an order is placed or pick is confirmed
- [ ] Low-stock products are visually flagged
- [ ] Detail view shows movement history

**US-006: Stock reservation on order**
As the system, I want to reserve inventory when an order is confirmed so that two salesmen don't promise the same stock.
Acceptance Criteria:
- [ ] Confirming an order decreases available quantity by ordered amount
- [ ] Cancelling an order releases reserved quantity
- [ ] Partial stock reservation is supported (backorder remaining)

### Epic: Order Management

**US-007: Create and submit order**
As a salesman, I want to create an order, select products with quantities, and submit it so that the customer's request is captured.
Acceptance Criteria:
- [ ] Select customer from existing list
- [ ] Search and add products with quantities
- [ ] See live stock availability while building the order
- [ ] Submit order → status = draft
- [ ] Confirm order → status = confirmed, inventory reserved
- [ ] Order reference number auto-generated

**US-008: View order status**
As a salesman or customer, I want to see where an order is in the process so that I can give the customer an update.
Acceptance Criteria:
- [ ] Order timeline shows: draft → confirmed → picking → picked → delivered → invoiced
- [ ] Each status change is timestamped
- [ ] Salesman sees all their orders in a list view with status filters

### Epic: Warehouse Operations

**US-009: View and process pick lists**
As a warehouse worker, I want to see confirmed orders as pick lists so that I know what to pick.
Acceptance Criteria:
- [ ] Dashboard shows pending pick lists
- [ ] Pick list items grouped by warehouse location
- [ ] Mark items as picked individually or in bulk
- [ ] Mark backorder for items not in stock
- [ ] Complete pick list when all items picked

**US-010: Confirm pick accuracy**
As a warehouse worker, I want to confirm that what I picked matches the order so that the customer gets what they ordered.
Acceptance Criteria:
- [ ] System shows expected vs picked quantity
- [ ] Partial picks allowed with remaining items backordered
- [ ] Pick confirmation reduces physical inventory
- [ ] Order status updates to "picked" when complete

### Epic: Accounts Receivable

**US-011: Automatic receivable creation**
As an accountant, I want receivables created automatically when an order is delivered so that I don't have to enter them manually.
Acceptance Criteria:
- [ ] Receivable created on order delivery with full amount
- [ ] Customer balance updated
- [ ] Receivable shows in accounting dashboard

**US-012: Record payments**
As an accountant, I want to record payments against a receivable by method (cash, check, installment) so that the balance is accurate.
Acceptance Criteria:
- [ ] Record cash payment with amount and date
- [ ] Record check payment with check number
- [ ] Record installment payment with plan details
- [ ] Partial payments supported
- [ ] Customer balance recalculated automatically
- [ ] Payment history viewable per receivable and per customer

**US-013: Customer balance view**
As an accountant, I want to see a customer's total balance across all payment methods so that I know their standing.
Acceptance Criteria:
- [ ] Customer detail shows total balance
- [ ] Aging breakdown (current, 30, 60, 90+ days)
- [ ] Payment history per customer
- [ ] Outstanding vs paid breakdown

### Epic: Migration

**US-014: Import legacy data**
As an admin, I want to import data from my old system so that I don't have to re-enter everything.
Acceptance Criteria:
- [ ] Upload CSV files for products, customers, inventory, orders
- [ ] Preview imported data before committing
- [ ] Validation errors shown with line numbers
- [ ] Commit or rollback migration
- [ ] Phantom products flagged automatically during import

## 6. Functional Requirements

**FR-001: User authentication via Auth0**
Priority: P0
Description: Users sign in via Auth0 with email/password or social login. JWT token is validated on every API request. User role and business ID extracted from token claims.
Acceptance Criteria:
- [ ] Auth0 tenant configured with email/password + Google social login
- [ ] Nuxt auth module or Auth0 SDK handles login flow
- [ ] FastAPI middleware validates JWT on protected routes
- [ ] User record created/synced in local DB on first login
- [ ] Role stored in app_metadata returned in JWT
Related Stories: US-001, US-002

**FR-002: Role-based authorization**
Priority: P0
Description: API endpoints are protected by role-based decorators. Each role has defined access to specific resources.
Acceptance Criteria:
- [ ] Decorator `@requires_role("admin")` on FastAPI routes
- [ ] Unauthorized access returns 403
- [ ] Frontend conditionally renders screens based on role
- [ ] Admin can assign/change user roles
Related Stories: US-002

**FR-003: Product CRUD**
Priority: P0
Description: Full create, read, update, soft-delete for products. Search and filter capabilities.
Acceptance Criteria:
- [ ] Create product with all required fields
- [ ] Edit name, price, category, unit of measure, threshold
- [ ] Soft-delete (is_active = false)
- [ ] Search by name and SKU
- [ ] Filter by category and phantom status
Related Stories: US-003

**FR-004: Phantom product detection**
Priority: P1
Description: Scheduled task scans products with no order transactions in 12+ months and flags them as phantom.
Acceptance Criteria:
- [ ] Admin triggers scan via API
- [ ] Products with last_transaction_date > 12 months flagged
- [ ] Products with no orders ever and created > 12 months ago flagged
- [ ] Admin can deactivate flagged products in bulk
- [ ] Phantom products hidden from salesman order catalog
Related Stories: US-004

**FR-005: Real-time inventory tracking**
Priority: P0
Description: Inventory levels update in real time. WebSocket pushes changes to all connected clients.
Acceptance Criteria:
- [ ] Stock levels calculated as: physical quantity - reserved quantity
- [ ] Physical quantity decreases on pick confirmation
- [ ] Reserved quantity increases on order confirmation
- [ ] Reserved quantity decreases on order cancellation
- [ ] Low stock alert when available < threshold
- [ ] WebSocket broadcasts inventory changes to all users in same business
Related Stories: US-005, US-006

**FR-006: Order creation and confirmation**
Priority: P0
Description: Salesman creates order with line items, reviews, and confirms. Confirmation reserves inventory.
Acceptance Criteria:
- [ ] Order draft allows adding/removing products
- [ ] Stock availability shown during order composition
- [ ] Confirmation validates stock availability
- [ ] On confirm: inventory reserved, order status = confirmed
- [ ] Order number auto-generated (e.g., ORD-00001)
- [ ] Cancellation releases reserved inventory
Related Stories: US-007, US-008

**FR-007: Pick list generation**
Priority: P0
Description: On order confirmation, a pick list is automatically created for warehouse.
Acceptance Criteria:
- [ ] Pick list created with all order items
- [ ] Items grouped by warehouse location
- [ ] Pick list visible in warehouse dashboard
- [ ] New pick list count shown in warehouse nav
Related Stories: US-009

**FR-008: Pick list processing**
Priority: P0
Description: Warehouse worker picks items, confirms picks, handles backorders.
Acceptance Criteria:
- [ ] Mark individual items as picked
- [ ] Mark items as backordered with reason
- [ ] Complete pick list updates physical inventory
- [ ] Order status updated to "picked" or "partially picked"
- [ ] Backordered items flagged for reorder
Related Stories: US-009, US-010

**FR-009: Automatic receivable creation**
Priority: P0
Description: When order status changes to "delivered," a receivable is automatically created.
Acceptance Criteria:
- [ ] Receivable amount = order total
- [ ] Customer balance increases
- [ ] Receivable visible in accounting dashboard
- [ ] Due date calculated from order delivery + configurable payment terms
Related Stories: US-011

**FR-010: Multi-payment method recording**
Priority: P1
Description: Accountant records payments by method against a receivable.
Acceptance Criteria:
- [ ] Record cash payment
- [ ] Record check payment with check number, bank, date
- [ ] Record installment with number of installments, frequency, amounts
- [ ] Partial payments supported
- [ ] Receivable balance auto-calculated
- [ ] Payment reference number tracked
Related Stories: US-012

**FR-011: Customer balance and aging**
Priority: P1
Description: Customer view shows total balance, aging breakdown, and payment history.
Acceptance Criteria:
- [ ] Balance = sum of all open receivables - sum of all payments
- [ ] Aging: current, 30, 60, 90+ days buckets
- [ ] Payment history sorted by date descending
- [ ] Can drill down to specific receivable
Related Stories: US-013

**FR-012: Legacy data migration**
Priority: P1
Description: CSV import for legacy data with preview and commit/rollback.
Acceptance Criteria:
- [ ] Upload CSV with configurable column mapping
- [ ] Preview shows: product count, customer count, inventory count, order count
- [ ] Validation errors with line numbers
- [ ] Commit writes data to production tables
- [ ] Rollback reverses the commit
- [ ] Phantom flagging runs automatically on import
Related Stories: US-014

**FR-013: Real-time WebSocket notifications**
Priority: P0
Description: WebSocket connections broadcast order and inventory changes to all connected clients within the same business.
Acceptance Criteria:
- [ ] New order confirmed → notification to warehouse
- [ ] Pick completed → notification to salesman and accountant
- [ ] Inventory changes broadcast to all salesmen
- [ ] Payment recorded → notification updates receivable view
- [ ] WebSocket reconnects automatically on disconnect
Related Stories: US-005, US-008, US-009, US-011

**FR-014: Dashboard by role**
Priority: P1
Description: Each role sees a relevant summary dashboard on login.
Acceptance Criteria:
- [ ] Salesman: open orders, low stock alerts, recent orders
- [ ] Warehouse: pending pick lists count, active picks, completed today
- [ ] Accountant: pending receivables, overdue alerts, today's payments
- [ ] Admin: all of the above + user management link
Related Stories: US-001, US-002

## 7. Non-Functional Requirements

### Performance
- Page load (LCP): < 2s on 3G connection
- Time to Interactive: < 3s
- API response time (p95): < 200ms for read endpoints, < 500ms for write endpoints
- WebSocket message latency: < 500ms from event to client receipt
- Inventory query response: < 100ms for full catalog
- Bundle size: < 200KB initial JS

### Security
- OWASP Top 10 addressed
- Auth0 JWT tokens expire every 24 hours; refresh token flow implemented
- Rate limiting: 10 requests/second per user on auth endpoints, 100/second on read endpoints
- CORS restricted to frontend origin only
- SQL injection prevention via SQLAlchemy parameterized queries
- Input validation via Pydantic schemas on all endpoints
- Sentry scrubs PII and tokens from error payloads

### Accessibility
- WCAG 2.1 AA compliance target
- All forms keyboard navigable
- Screen reader tested (NVDA on Windows, VoiceOver on macOS)
- Color contrast ratios meet WCAG AA minimums
- Focus indicators on all interactive elements

### Scalability
- Support 10 concurrent users per business (30 businesses = 300 concurrent users on initial infrastructure tier)
- PostgreSQL connection pooling via PgBouncer
- FastAPI async handlers for non-blocking I/O
- WebSocket connections: 1 per active user per business
- Cache immutable data (product catalog) with Redis (optional — add when needed)

### Reliability
- 99.5% uptime target for cloud deployment
- Graceful degradation when Auth0, Stripe, or PostHog are unreachable
- WebSocket auto-reconnect with exponential backoff
- Database backups automated daily for cloud, configurable for on-prem
- Migration rollback capability

## 8. UI/UX Requirements

Visual tokens not yet defined. Run the **Design System** skill before implementation begins to generate `docs/design.md` with color palette, typography, spacing, components, and design tokens.

This section covers structural UX — layouts, states, interactions, and which screens exist.

### Screen: Login
Route: `/login`
Purpose: User authenticates via Auth0
Layout: Centered card with Nova logo, "Sign in with Auth0" button. Links: "Don't have an account? Contact your admin."
States:
- **Loading:** Button shows spinner during Auth0 redirect
- **Error:** Inline error if Auth0 configuration fails
- **Success:** Redirect to role-specific dashboard

### Screen: Dashboard
Route: `/dashboard`
Purpose: Role-specific landing page showing relevant summary
Layout: Top navbar with Nova logo + user menu (profile, logout). Sidebar with role-specific nav items. Main content area.
States:
- **Loading:** Skeleton cards for each summary widget
- **Empty:** "Welcome to Nova! [Next action based on role: add a product, create an order, etc.]"
- **Populated:** Summary cards (count + list preview per section)
- **Error:** "Couldn't load dashboard. Retry" with retry button

Role-specific nav:
- Admin: Products, Orders, Warehouse, Accounting, Suppliers, Customers, Users, Settings, Migration
- Salesman: Products, Orders, Customers
- Warehouse: Pick Lists, Inventory
- Accountant: Receivables, Customers

### Screen: Products List
Route: `/products`
Purpose: Browse and search product catalog
Layout: Search bar + filter row (category, phantom toggle) + table view with columns: SKU, Name, Category, Available Stock, Price, Status
Interactions:
- Click row → navigate to product detail
- "Add Product" button → modal form
- Phantom toggle filter (on/off)
- Search debounced (300ms)
States:
- **Empty:** "No products yet. Add your first product to get started." + CTA button
- **Loading:** Table skeleton with 5 rows
- **Populated:** Product rows with inline stock indicator (green/yellow/red)
- **Error:** "Failed to load products. [Retry]"

### Screen: Product Detail
Route: `/products/{id}`
Purpose: View and edit product details
Layout: Two-column layout — left: product fields (editable), right: inventory info + stock movement history
Interactions:
- Edit inline → save button
- Deactivate product → confirmation modal
- Stock movement history table with date, type, quantity change, reference
States:
- **Loading:** Form skeleton
- **Error:** "Product not found" or "Failed to load"
- **Populated:** Full product view

### Screen: Create Order
Route: `/orders/new`
Purpose: Salesman creates a new order
Layout: Step form — Step 1: Select customer (search/dropdown). Step 2: Add line items (search products, enter qty, see live stock). Step 3: Review order. Step 4: Confirm.
Interactions:
- Product search with autocomplete and stock display
- Quantity input with max = available stock
- Running total at bottom
- "Save as Draft" / "Confirm" buttons
- Phantom products excluded from catalog
States:
- **Empty customer:** "Start by selecting a customer"
- **Empty items:** "Add products to this order"
- **Low stock:** Yellow warning icon next to quantity
- **Out of stock:** Red indicator, quantity disabled

### Screen: Order List
Route: `/orders`
Purpose: View all orders with filters
Layout: Filter bar (status, date range, customer, salesman) + table (Order#, Customer, Date, Total, Status, Actions)
Interactions:
- Click row → order detail
- Status filter chips
- Date range picker
States:
- **Empty:** "No orders found. Create your first order."
- **Loading:** Table skeleton

### Screen: Order Detail
Route: `/orders/{id}`
Purpose: View full order with timeline and line items
Layout: Header (Order#, status, customer, salesman, date) + timeline (vertical steps showing status changes) + line items table + total
Interactions:
- Cancel button (if status is draft/confirmed)
- Status badge with color coding
States:
- **Loading:** Skeleton
- **Error:** "Order not found"

### Screen: Warehouse Dashboard
Route: `/warehouse`
Purpose: See and process pick lists
Layout: Two sections — Pending picks (cards with product count and customer name) + Completed today (list)
Interactions:
- Click pending pick → pick list detail
- "Start picking" button
States:
- **Empty:** "No picks waiting. Once a salesman places an order, it'll show up here automatically."
- **Loading:** Skeleton cards

### Screen: Pick List Detail
Route: `/warehouse/pick-lists/{id}`
Purpose: Process individual pick list
Layout: Order info header + items table grouped by location (Location header, items beneath) + completion bar
Interactions:
- Checkbox per item → mark as picked
- "Backorder" button per item
- "Complete Pick List" button when all items handled
- Items sorted by warehouse location
States:
- **Loading:** Skeleton
- **In Progress:** Items with checkboxes, completion percentage
- **Completed:** All items checked, "Pick Complete" badge
- **Partially Completed:** Some backordered, notes field for reason

### Screen: Accounting Dashboard
Route: `/accounting`
Purpose: See and manage receivables
Layout: Summary cards (Total outstanding, Overdue, Paid this month) + receivables table (Customer, Amount, Balance, Status, Due, Actions)
Interactions:
- Click receivable → receivable detail
- Filter by status (pending, overdue, paid)
States:
- **Empty:** "No receivables. Once orders are delivered, receivables will appear here automatically."
- **Loading:** Skeleton cards

### Screen: Receivable Detail
Route: `/accounting/receivables/{id}`
Purpose: View receivable and record payments
Layout: Header (Customer, Amount, Balance, Status) + payment method tabs (Cash, Check, Installment) + payment history table
Interactions:
- Select payment method tab → form appears
- Record payment → balance updates
- Payment history shows all recorded payments
States:
- **Loading:** Skeleton
- **Error:** "Receivable not found"
- **Paid:** "Fully paid" badge, no payment form

### Screen: Customer Detail
Route: `/customers/{id}`
Purpose: View customer info, balance, and payment history
Layout: Customer info header + balance aging breakdown + receivables list + payment history
States:
- **Loading:** Skeleton
- **Empty orders:** "No orders yet"
- **Populated:** Full customer view

### Screen: Migration
Route: `/admin/migration`
Purpose: Import data from legacy system
Layout: Step wizard — Step 1: Upload CSV files. Step 2: Map columns. Step 3: Preview (counts per entity, validation errors). Step 4: Commit or rollback.
Interactions:
- Drag & drop CSV upload
- Column mapping dropdowns
- "Preview Import" button
- "Commit" / "Rollback" buttons
States:
- **Empty:** Upload prompt
- **Validation errors:** Error list with line numbers
- **Preview:** Summary table with row counts
- **Committed:** "Migration complete — X products, Y customers, Z orders imported"
- **Rolled back:** "Migration rolled back successfully"

## 9. Auth Implementation

### Auth Flow
1. User visits Nova → redirected to Auth0 Universal Login page
2. User authenticates (email/password or Google social login)
3. Auth0 redirects to Nuxt callback page with authorization code
4. Nuxt exchanges code for JWT token via Auth0 SDK
5. JWT contains user ID, email, roles (in app_metadata), and business_id (in app_metadata)
6. FastAPI middleware validates JWT on every API request
7. On first login, FastAPI creates user record in local DB via `/api/v1/auth/callback`

### Auth0 Configuration
- Tenant: Nova (create in Auth0 dashboard)
- Application: Single Page Application (Nuxt)
- API: "Nova API" with identifier `https://api.novaerp.com`
- Connections: Database (email/password), Google
- Rules: Add role and business_id to app_metadata on user creation/update
- Actions: Post-login action syncs user to Nova DB

### FastAPI JWT Validation Middleware
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.config import settings

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.auth0_jwks,
            algorithms=["RS256"],
            audience=settings.auth0_api_audience,
            issuer=f"https://{settings.auth0_domain}/"
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
```

### Role-Based Access Decorator
```python
from functools import wraps
from fastapi import Depends, HTTPException

def requires_role(*roles: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user=Depends(get_current_user), **kwargs):
            user_role = user.get("https://novaerp.com/role")
            if user_role not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Protected Routes (Nuxt)
- `/products` — salesman, warehouse (read-only), admin
- `/orders` — salesman, admin
- `/warehouse` — warehouse, admin
- `/accounting` — accountant, admin
- `/admin/*` — admin only
- `/migration` — admin only

### User Session Management
- JWT stored in HttpOnly cookie or memory (Auth0 SDK default: in-memory)
- Token refresh via Auth0 silent auth (using iframe + refresh token rotation)
- Session timeout: 24 hours, or logout clears token

## 10. Payment Integration

### Payment Flow
1. Admin subscribes to Nova via Stripe Checkout
2. Free trial: 14 days, no payment method required
3. After trial, admin prompted to subscribe
4. Admin clicks "Subscribe" → redirected to Stripe Checkout
5. Stripe webhook (`checkout.session.completed`) → FastAPI updates business.subscription_status
6. Prorated billing for new users added mid-cycle
7. Invoices sent via Stripe (emailed to admin)

### Stripe Setup
- Products: "Nova Business" — $5/user/month, metered billing by number of users
- Or: "Nova Business" — $5/user/month, quantity-based (admin specifies user count)
- Webhook endpoint: `/api/v1/webhooks/stripe`
- Events to handle: `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, `customer.subscription.updated`, `customer.subscription.deleted`

### Price Configuration
```python
# Stripe price for $5/user/month
STRIPE_PRICE_ID_MONTHLY = "price_xxxxxxxxxxxxx"

# Free trial period: 14 days
TRIAL_PERIOD_DAYS = 14
```

### Subscription Gating
- API middleware checks `business.subscription_status` on write endpoints
- Active / trialing → allowed
- Past_due / canceled → read-only mode for 7 days, then blocked
- Webhook listener updates subscription status in real time

### Testing
- Use Stripe test mode with test card `4242 4242 4242 4242`
- Test webhooks via Stripe CLI: `stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe`
- Test subscription events: `stripe trigger checkout.session.completed`

## 11. Edge Cases & Error Handling

### Products
| Scenario | Expected Behavior | Priority |
|---|---|---|
| Create product with duplicate SKU | 409 Conflict — "SKU already exists" | P0 |
| Deactivate product with open orders | Prevent deactivation — "Product has open orders" with link to orders | P1 |
| Search with no results | "No products matching [query]. Try a different search term." | P0 |

### Orders
| Scenario | Expected Behavior | Priority |
|---|---|---|
| Confirm order with insufficient stock | Partial confirmation — confirm available qty, backorder the rest. Show backorder summary. | P0 |
| Cancel already-picked order | Allow cancellation but flag for warehouse — "Order was partially picked. Notify warehouse: items may need restocking." | P1 |
| Double-click confirm button | Idempotent — second click detects order is already confirmed, returns success without duplicating | P0 |
| Network failure during order creation | Order saved as draft. Show toast: "Saved as draft. You can submit when connected." | P0 |

### Pick Lists
| Scenario | Expected Behavior | Priority |
|---|---|---|
 | All items backordered | Pick list marked as "backordered" — no physical inventory changes | P1 |
 | Pick more than ordered quantity | Cap at ordered quantity. Show warning: "Cannot pick more than ordered." | P0 |
 | Two warehouse workers open same pick list | Pessimistic lock — second opener sees "being picked by [user] since [time]" | P1 |

### Inventory
| Scenario | Expected Behavior | Priority |
|---|---|---|
 | Receive goods not in catalog | Allow receipt with "create product" prompt if product doesn't exist | P2 |
 | Negative stock due to data error | Allow (with warning flag) but log movement for audit. Show "Negative stock — check movement history." | P1 |
 | Concurrent inventory updates | Database row-level lock on inventory record during update. Retry on conflict. | P0 |

### Accounting
| Scenario | Expected Behavior | Priority |
|---|---|---|
 | Overpay a receivable | Show warning: "Payment exceeds balance by [amount]. Create credit note?" | P1 |
 | Record payment for already-paid receivable | 409 — "Receivable is fully paid. No additional payment needed." | P0 |
 | Delete a payment | Soft-delete with reason. Recalculate receivable balance. Add audit log entry. | P1 |

### Auth
| Scenario | Expected Behavior | Priority |
|---|---|---|
 | Auth0 unreachable | Show "We're having trouble connecting to our auth provider. Please try again in a few minutes." Allow retry. | P0 |
 | Token expires mid-session | Auto-refresh via Auth0 silent auth. If refresh fails, redirect to login with "Session expired. Please sign in again." | P0 |
 | User with no role assigned | Default to "salesman" role. Show banner: "Contact your admin to set your role." | P1 |

### Migration
| Scenario | Expected Behavior | Priority |
|---|---|---|
 | CSV file has wrong column names | Show column mapping UI with auto-detect and manual override | P1 |
 | Duplicate SKUs in import | Flag in preview: "X products with duplicate SKUs. Keep first or skip duplicates?" | P1 |
 | Migration fails mid-commit | Rollback automatically. Show error: "Migration failed at step [X]. All data has been rolled back." | P0 |
 | Large CSV (>100K rows) | Chunked import with progress bar. Show "Importing row X of Y..." | P1 |

### WebSocket
| Scenario | Expected Behavior | Priority |
|---|---|---|
 | Client disconnects briefly | Auto-reconnect with exponential backoff (1s, 2s, 4s, 8s, max 30s) | P0 |
 | WebSocket message not delivered | Client fetches latest state on reconnection via GET endpoint. No message loss guarantee for short-lived data. | P1 |
 | Business instance runs on-prem with restrictive network | WebSocket falls back to polling (configurable interval, default 30s) | P1 |

## 12. Dependencies & Integrations

### Core Dependencies

**Frontend (package.json):**
```json
{
    "nuxt": "^3.x",
    "vue": "^3.x",
    "@nuxtjs/auth-next": "^1.x",
    "vue-router": "^4.x",
    "pinia": "^2.x",
    "nuxt-posthog": "^1.x",
    "@nuxtjs/sentry": "^7.x",
    "vueuse": "^10.x",
    "tailwindcss": "^3.x",
    "headlessui": "^1.x",
    "typescript": "^5.x"
}
```

**Backend (requirements.txt):**
```
fastapi==0.115.*
uvicorn[standard]==0.32.*
sqlalchemy[asyncio]==2.0.*
asyncpg==0.30.*
alembic==1.14.*
python-jose[cryptography]==3.3.*
auth0-python==4.*
pydantic==2.*
pydantic-settings==2.*
stripe==11.*
sentry-sdk[fastapi]==2.*
resend==0.*
posthog==3.*
python-multipart==0.*
websockets==13.*
httpx==0.*
python-dotenv==1.*
```

### Development Dependencies
```json
{
    "eslint": "^9.x",
    "prettier": "^3.x",
    "husky": "^9.x",
    "lint-staged": "^15.x",
    "vitest": "^2.x",
    "playwright": "^1.x"
}
```

### Third-Party Services

| Service | Purpose | Pricing Tier | Requirements |
|---|---|---|---|
| Auth0 | Authentication, SSO, role management | Free tier: 7K MAUs | `AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET`, `AUTH0_API_AUDIENCE` |
| Stripe | Subscription billing, payment processing | Pay-as-you-go (2.9% + $0.30) | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_MONTHLY` |
| PostHog | Product analytics, session replay, feature flags | Free: 1M events/month | `POSTHOG_API_KEY`, `POSTHOG_HOST` |
| Resend | Transactional email (welcome, receipts, notifications) | Free: 3,000 emails/month | `RESEND_API_KEY` |
| Sentry | Error and performance monitoring | Free: 5K errors/month | `SENTRY_DSN` |
| Neon | Serverless PostgreSQL hosting | Free: 0.5GB storage, 100hr compute/mo | `DATABASE_URL` |

## 13. Out of Scope

| Feature | Why Excluded | When to Reconsider |
|---|---|---|
| Full accounting (GL, P&L, balance sheet) | Accounts receivable is enough to prove the flow. Financial accounting is a separate product. | After MVP, when customers ask for it |
| POS module | Disconnected POS is a pain point but solving the inventory cascade is the bigger win. | Post-MVP, as a paid add-on module |
| Budgeting and forecasting | Not needed until the business has enough transaction history in Nova. | 6+ months post-launch |
| Multi-warehouse | Makka has one warehouse. Supporting multiple warehouses adds complexity without a customer. | When the second customer with multiple warehouses signs up |
| Native mobile apps | Progressive web app (PWA) is sufficient for MVP. | Post-MVP, based on user demand |
| AI/automation features | Tempting but doesn't test the core assumption. | After product-market fit is established |
| Construction industry support | Explicitly a future expansion. Nova is F&B-first. | 12+ month roadmap |
| Open-source community infrastructure | Repo can be public, but community infrastructure (docs site, forum, contributor guidelines) is deferred. | After MVP, when external interest emerges |
| Reporting and BI dashboards | Invoice, inventory aging, and order reports are P2. Manual CSV export for now. | Post-MVP, as P2 features |
| API documentation portal | Auto-generated OpenAPI docs via FastAPI Swagger are sufficient for MVP. | When third-party developers request access |

## 14. Open Questions

| Question | Options | Tradeoffs | Recommended Default |
|---|---|---|---|
| Phantom product detection: auto-flag vs manual trigger? | Auto-flag (scheduled) / Manual trigger / Both | Auto ensures catalog stays clean; manual gives admin control | Both — auto-flag weekly, manual trigger available |
| Invoice numbering format? | Sequential (ORD-00001) / Date-based (20260702-001) / UUID | Sequential is human-friendly, date-based shows chronology | Sequential with optional date prefix config |
| Multi-instance deployment: how to handle version upgrades for on-prem? | Docker image tags / Git pull + build / Package manager | Docker tags are simplest for on-prem updates | Docker Compose with version-tagged images |
| Payment installments: track as separate payment lines or single receivable with schedule? | Separate payments / Single receivable with installment schedule | Separate is simpler to implement; schedule gives better visibility | Separate payment lines with installment reference number |
| WebSocket vs Server-Sent Events for real-time updates? | WebSocket (bidirectional) / SSE (unidirectional + client HTTP for writes) | WebSocket handles real-time both ways; SSE simpler but read-only | WebSocket for MVP (FastAPI has native support), SSE as fallback |
| PWA or full responsive SPA for mobile access? | PWA (offline support) / Responsive SPA (always online) | PWA adds service worker complexity but works offline | PWA as stretch goal for MVP, responsive SPA as minimum |
| Open-source license choice? | AGPLv3 (like Odoo) / Apache 2.0 / MIT | AGPLv3 protects against proprietary forks; MIT is most permissive | AGPLv3 — aligns with Odoo model, protects the business |
