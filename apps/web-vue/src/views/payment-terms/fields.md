# Fields — Payment Terms

## Database columns (`Nova.T0096`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| name | `VARCHAR(100)` | Yes | — | Term display name |
| code | `VARCHAR(20)` | Yes | — | Unique code |
| description | `TEXT` | No | — | Description |
| due_days | `INT` | No | 30 | Days until payment due |
| discount_percentage | `DECIMAL` | No | 0 | Early payment discount % |
| discount_days | `INT` | No | 0 | Days within which discount applies |
| is_default | `BOOLEAN` | No | FALSE | Default flag |
| is_active | `BOOLEAN` | No | TRUE | Soft-delete |

## Pydantic models

### `PaymentTermCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| name | `str` | Yes | Max 100 |
| code | `str` | Yes | Max 20 |
| description | `str?` | No | — |
| due_days | `int` | No | Default 30 |
| discount_percentage | `float` | No | 0–100 |
| discount_days | `int` | No | Default 0 |
| is_default | `bool` | No | Default False |

### `PaymentTermUpdate`
All fields Optional.

### `PaymentTermResponse`
Extends `AuditMixin`.
