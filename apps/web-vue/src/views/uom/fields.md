# Fields — Units of Measure

## Database columns (`Nova.T0001`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| uom_code | `VARCHAR(10)` | Yes | — | Short UOM code (e.g. EA, KG, L) |
| uom_name | `VARCHAR(50)` | Yes | — | Full UOM name (e.g. Each, Kilogram) |
| category | `VARCHAR` | No | `Quantity` | UOM category (Quantity, Weight, Volume, Length) |
| is_base_unit | `BOOLEAN` | No | `FALSE` | Is this the base unit for its category |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| created_by | `INT` | No | — | FK to T0021 |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_by | `INT` | No | — | FK to T0021 |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### UOMCreate
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| uom_code | `str` | Yes | max 10 chars |
| uom_name | `str` | Yes | max 50 chars |
| category | `str` | No | defaults to `Quantity` |
| is_base_unit | `bool` | No | defaults to `False` |
| is_active | `bool` | No | defaults to `True` |

### UOMUpdate
All fields Optional. Same types as Create.

### UOMResponse
Extends `AuditMixin` — adds `created_at`, `created_by`, `updated_at`, `updated_by`, `update_number`.
