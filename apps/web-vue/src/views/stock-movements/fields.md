# Fields — Stock Movements

## Database columns (`Nova.T0064`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| product_id | `INT` | Yes | — | FK to T0003 (Products) |
| warehouse_id | `INT` | Yes | — | FK to T0008 (Warehouses) |
| movement_type | `VARCHAR(30)` | Yes | — | IN, OUT, TRANSFER_IN, TRANSFER_OUT, ADJUSTMENT, RETURN |
| reference_type | `VARCHAR(30)` | No | — | e.g., Sales Order, Purchase Order |
| reference_id | `INT` | No | — | FK to reference document |
| qty_change | `NUMERIC` | Yes | — | Positive = stock in, Negative = stock out |
| balance_after | `NUMERIC` | No | `0` | Resulting stock balance |
| description | `TEXT` | No | — | Movement description |
| movement_date | `TIMESTAMPTZ` | No | `now()` | When the movement occurred |
| created_by | `INT` | No | — | User who created |
| created_at | `TIMESTAMPTZ` | No | `now()` | Creation timestamp |

## Pydantic models

### `StockMovementCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| product_id | `int` | Yes | |
| warehouse_id | `int` | Yes | |
| movement_type | `str` | Yes | Max 30 chars |
| reference_type | `Optional[str]` | No | |
| reference_id | `Optional[int]` | No | |
| qty_change | `float` | Yes | Positive or negative |
| balance_after | `float` | No | Default `0` |
| description | `Optional[str]` | No | |

### `StockMovementResponse`
Includes: `id`, `product_id`, `warehouse_id`, `movement_type`, `reference_type`, `reference_id`, `qty_change`, `balance_after`, `description`, `movement_date`, `created_by`, `created_at`.
