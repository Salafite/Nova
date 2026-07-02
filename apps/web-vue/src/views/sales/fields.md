# Fields — Sales Orders

## Database columns (`Nova.T0012`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| order_number | `VARCHAR(30)` | Yes | — | Unique order number |
| customer_id | `INT` | Yes | — | FK to T0010 (Customers) |
| subtotal | `NUMERIC(12,2)` | No | `0` | Line items subtotal |
| tax | `NUMERIC(12,2)` | No | `0` | Tax amount |
| grand_total | `NUMERIC(12,2)` | No | `0` | Total including tax |
| status | `order_status` | No | `Pending` | Order status enum |
| order_date | `DATE` | No | `CURRENT_DATE` | Order date |
| notes | `TEXT` | No | — | Order notes |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### `SalesOrderCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| order_number | `str` | Yes | Max 30 chars |
| customer_id | `int` | Yes | FK to T0010 |
| subtotal | `float` | No | Default `0` |
| tax | `float` | No | Default `0` |
| grand_total | `float` | No | Default `0` |
| status | `str` | No | Default `'Pending'` |
| order_date | `date` | No | Default today |
| notes | `Optional[str]` | No | |

### `SalesOrderUpdate`
All fields Optional for partial update.

### `SalesOrderResponse`
Extends `AuditMixin` — adds `created_at`, `created_by`, `updated_at`, `updated_by`, `update_number`.
