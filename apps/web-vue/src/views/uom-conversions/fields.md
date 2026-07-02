# Fields — UOM Conversions

## Database columns (`Nova.T0002`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| from_uom_id | `INT` | Yes | — | FK to T0001 (UOM) |
| to_uom_id | `INT` | Yes | — | FK to T0001 (UOM) |
| factor | `NUMERIC(18,6)` | Yes | — | Conversion multiplier (> 0) |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### `UOMConvCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| from_uom_id | `int` | Yes | FK to T0001 |
| to_uom_id | `int` | Yes | FK to T0001 |
| factor | `float` | Yes | Must be > 0 |

### `UOMConvUpdate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| from_uom_id | `Optional[int]` | No | |
| to_uom_id | `Optional[int]` | No | |
| factor | `Optional[float]` | No | Must be > 0 if provided |

### `UOMConvResponse`
Extends `AuditMixin` — adds `created_at`, `created_by`, `updated_at`, `updated_by`, `update_number`.
