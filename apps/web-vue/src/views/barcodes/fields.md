# Fields — Barcodes

## Database columns (`Nova.T0004`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| product_id | `INT` | Yes | — | FK to T0003 (Products, CASCADE) |
| barcode | `VARCHAR(100)` | Yes | — | Unique barcode string |
| barcode_type | `VARCHAR(20)` | No | `EAN13` | Type (EAN13, EAN8, UPC, CODE128, QR) |
| is_primary | `BOOLEAN` | No | `FALSE` | Primary flag for product |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### `BarcodeCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| product_id | `int` | Yes | FK to T0003 |
| barcode | `str` | Yes | Max 100 chars |
| barcode_type | `str` | No | Default `EAN13` |
| is_primary | `bool` | No | Default `False` |

### `BarcodeUpdate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| product_id | `Optional[int]` | No | |
| barcode | `Optional[str]` | No | |
| barcode_type | `Optional[str]` | No | |
| is_primary | `Optional[bool]` | No | |

### `BarcodeResponse`
Extends `AuditMixin` — adds audit fields.
