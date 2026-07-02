# Fields — Payment Methods

## Database columns (`Nova.T0097`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| name | `VARCHAR(100)` | Yes | — | Method display name |
| code | `VARCHAR(20)` | Yes | — | Unique code |
| description | `TEXT` | No | — | Description |
| is_default | `BOOLEAN` | No | FALSE | Default flag |
| is_active | `BOOLEAN` | No | TRUE | Soft-delete |

## Pydantic models

### `PaymentMethodCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| name | `str` | Yes | Max 100 |
| code | `str` | Yes | Max 20 |
| description | `str?` | No | — |
| is_default | `bool` | No | Default False |

### `PaymentMethodUpdate`
All fields Optional.

### `PaymentMethodResponse`
Extends `AuditMixin`.
