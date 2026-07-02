# Fields — Suppliers

## Database columns (`Nova.T0011`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| name | `VARCHAR(200)` | Yes | — | Supplier name |
| category | `VARCHAR(100)` | No | — | Supplier category |
| phone | `VARCHAR(30)` | No | — | Phone number |
| email | `VARCHAR(200)` | No | — | Email address |
| payment_terms | `VARCHAR(100)` | No | — | Payment terms |
| rating | `SMALLINT` | No | `0` | Rating 0-5 |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### `SupplierCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| name | `str` | Yes | Max 200 chars |
| category | `Optional[str]` | No | Max 100 chars |
| phone | `Optional[str]` | No | Max 30 chars |
| email | `Optional[str]` | No | Max 200 chars |
| payment_terms | `Optional[str]` | No | Max 100 chars |
| rating | `int` | No | Default `0`, 0-5 |
| is_active | `bool` | No | Default `True` |

### `SupplierUpdate`
All fields Optional for partial update.

### `SupplierResponse`
Extends `AuditMixin` — adds `created_at`, `created_by`, `updated_at`, `updated_by`, `update_number`.
