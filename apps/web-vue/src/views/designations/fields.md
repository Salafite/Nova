# Fields — Designations

## Database columns (`Nova.T0029`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| designation_code | `VARCHAR(20)` | Yes | — | Unique code |
| designation_name | `VARCHAR(100)` | Yes | — | Display name |
| department_id | `INT` | No | — | FK to T0028 (Department) |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### DesignationCreate
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| designation_code | `str` | Yes | Max 20 chars |
| designation_name | `str` | Yes | Max 100 chars |
| department_id | `Optional[int]` | No | FK to T0028 |
| is_active | `bool` | No | Default: `True` |

### DesignationUpdate
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| All fields | `Optional` | No | Partial update supported |

### DesignationResponse
Extends `AuditMixin` — adds `created_at`, `created_by`, `updated_at`, `updated_by`, `update_number`.
