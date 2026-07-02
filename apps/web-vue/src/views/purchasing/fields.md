# Fields — Purchase Orders

## Database columns (`Nova.T0014`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| order_number | `VARCHAR(30)` | Yes | — | Unique PO number |
| supplier_id | `INT` | Yes | — | FK to T0011 (Suppliers) |
| total | `NUMERIC(12,2)` | No | `0` | Order total |
| status | `po_status` | No | `Pending` | PO status enum |
| order_date | `DATE` | No | `CURRENT_DATE` | Order date |
| expected_date | `DATE` | No | — | Expected delivery date |
| notes | `TEXT` | No | — | PO notes |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### `PurchaseOrderCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| order_number | `str` | Yes | Max 30 chars |
| supplier_id | `int` | Yes | FK to T0011 |
| total | `float` | No | Default `0` |
| status | `str` | No | Default `'Pending'` |
| order_date | `date` | No | Default today |
| expected_date | `Optional[date]` | No | |
| notes | `Optional[str]` | No | |

### `PurchaseOrderUpdate`
All fields Optional for partial update.

### `PurchaseOrderResponse`
Extends `AuditMixin` — adds `created_at`, `created_by`, `updated_at`, `updated_by`, `update_number`.
