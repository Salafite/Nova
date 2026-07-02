# Fields — Chart of Accounts

## Database columns (`Nova.T0026`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| account_code | `VARCHAR(20)` | Yes | — | Unique account code |
| account_name | `VARCHAR(100)` | Yes | — | Account display name |
| account_type | `VARCHAR(50)` | Yes | — | Asset, Liability, Equity, Revenue, Expense |
| currency | `VARCHAR(3)` | No | USD | Currency code |
| is_active | `BOOLEAN` | No | TRUE | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | now() | Audit |
| updated_at | `TIMESTAMPTZ` | No | now() | Audit |
| update_number | `INT` | No | 1 | Optimistic lock |

## Pydantic models

### `COACreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| account_code | `str` | Yes | Max 20 chars |
| account_name | `str` | Yes | Max 100 chars |
| account_type | `str` | Yes | One of: Asset, Liability, Equity, Revenue, Expense |
| currency | `str` | No | Default USD |
| is_active | `bool` | No | Default True |

### `COAUpdate`
All fields Optional for partial update.

### `COAResponse`
Extends `AuditMixin` — adds `created_at`, `created_by`, `updated_at`, `updated_by`, `update_number`.
