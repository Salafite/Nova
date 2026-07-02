# Fields — Stock Levels (Inventory)

## Database columns (`Nova.T0009`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| product_id | `INT` | Yes | — | FK to T0003 (Products) |
| warehouse_id | `INT` | Yes | — | FK to T0008 (Warehouses) |
| qty | `NUMERIC` | Yes | `0` | Current quantity on hand (>= 0) |
| reorder_level | `NUMERIC` | Yes | `0` | Threshold below which reorder is needed |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_by | `INT` | No | — | Audit |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### `StockLevelCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| product_id | `int` | Yes | |
| warehouse_id | `int` | Yes | |
| qty | `float` | No | Default `0`, >= 0 |
| reorder_level | `float` | No | Default `0`, >= 0 |

### `StockLevelResponse`
Extends `AuditMixin` — adds audit fields.
