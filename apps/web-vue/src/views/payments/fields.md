# Fields — Payments

## Database columns (`Nova.T0091`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| payment_date | `DATE` | Yes | — | Date of payment |
| invoice_id | `INT` | No | — | FK to T0090 (Invoice) |
| partner_id | `INT` | Yes | — | Customer or Supplier ID |
| amount | `NUMERIC` | Yes | — | Payment amount (> 0) |
| payment_method | `VARCHAR(50)` | Yes | — | Cash, Bank Transfer, Card |
| reference | `VARCHAR(100)` | No | — | External reference |
| status | `VARCHAR(20)` | No | `'Completed'` | Completed, Pending, Failed, Cancelled |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### PaymentCreate
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| payment_date | `date` | Yes | — |
| invoice_id | `Optional[int]` | No | FK to T0090 |
| partner_id | `int` | Yes | Customer or Supplier |
| amount | `float` | Yes | Must be > 0 |
| payment_method | `str` | Yes | Max 50 chars |
| reference | `Optional[str]` | No | Max 100 chars |
| status | `str` | No | Default: `'Completed'` |

### PaymentUpdate
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| All fields | `Optional` | No | Partial update supported |

### PaymentResponse
Extends `AuditMixin` — adds `created_at`, `created_by`, `updated_at`, `updated_by`, `update_number`.
