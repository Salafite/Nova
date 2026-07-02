# Fields — Warehouses

## Database columns (`Nova.T0008`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| name | `VARCHAR(100)` | Yes | — | Unique warehouse name |
| location | `VARCHAR(200)` | No | — | Physical location |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_by | `INT` | No | — | Audit |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### `WarehouseCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| name | `str` | Yes | Max 100 chars |
| location | `Optional[str]` | No | Max 200 chars |
| is_active | `bool` | No | Default `True` |

### `WarehouseUpdate`
All fields Optional for partial update.

### `WarehouseResponse`
Extends `AuditMixin` — adds audit fields.
