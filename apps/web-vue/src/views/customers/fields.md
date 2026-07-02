# Fields — Customers

## Database columns (`Nova.T0010`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| name | `VARCHAR(200)` | Yes | — | Customer name |
| group_name | `VARCHAR(100)` | No | `Retail` | Customer group |
| phone | `VARCHAR(30)` | No | — | Phone number |
| email | `VARCHAR(200)` | No | — | Email address |
| credit_limit | `NUMERIC(12,2)` | No | `0` | Credit limit (>= 0) |
| balance | `NUMERIC(12,2)` | No | `0` | Current balance (>= 0) |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### `CustomerCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| name | `str` | Yes | Max 200 chars |
| group_name | `str` | No | Default `Retail` |
| phone | `Optional[str]` | No | Max 30 chars |
| email | `Optional[str]` | No | Max 200 chars |
| credit_limit | `float` | No | Default `0`, >= 0 |
| balance | `float` | No | Default `0`, >= 0 |
| is_active | `bool` | No | Default `True` |

### `CustomerUpdate`
All fields Optional for partial update.

### `CustomerResponse`
Extends `AuditMixin` — adds `created_at`, `created_by`, `updated_at`, `updated_by`, `update_number`.
