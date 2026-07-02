# Fields — Products

## Database columns (`Nova.T0003`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| name | `VARCHAR(200)` | Yes | — | Product name |
| sku | `VARCHAR(50)` | Yes | — | Stock keeping unit code |
| price | `NUMERIC` | No | `0` | Sales price |
| cost_price | `NUMERIC` | No | `0` | Cost/unit price |
| category | `VARCHAR(100)` | No | — | Product category |
| brand | `VARCHAR(100)` | No | — | Brand name |
| tax_rate | `NUMERIC` | No | `0.05` | Tax rate (e.g. 0.05 = 5%) |
| image_url | `VARCHAR(500)` | No | — | Product image URL |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| created_by | `INT` | No | — | FK to T0021 |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_by | `INT` | No | — | FK to T0021 |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### ProductCreate
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| name | `str` | Yes | max 200 chars |
| sku | `str` | Yes | max 50 chars |
| price | `float` | No | defaults to `0`, min 0 |
| cost_price | `Optional[float]` | No | defaults to `0`, min 0 |
| category | `Optional[str]` | No | max 100 chars |
| brand | `Optional[str]` | No | max 100 chars |
| tax_rate | `float` | No | defaults to `0.05`, min 0 |
| image_url | `Optional[str]` | No | max 500 chars |
| is_active | `bool` | No | defaults to `True` |

### ProductUpdate
All fields Optional. Same types as Create.

### ProductResponse
Extends `AuditMixin` — adds `created_at`, `created_by`, `updated_at`, `updated_by`, `update_number`.
