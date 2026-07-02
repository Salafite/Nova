# Fields — Attributes

## Database columns (`Nova.T0005`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| attribute_name | `VARCHAR(50)` | Yes | — | Unique attribute name |
| attribute_type | `VARCHAR(20)` | No | `Text` | Type: Text, Number, Date, Boolean, Select |
| is_required | `BOOLEAN` | No | `FALSE` | Required flag |
| sort_order | `INT` | No | `0` | Display sort order |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### `AttrDefCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| attribute_name | `str` | Yes | Max 50 chars |
| attribute_type | `str` | No | Default `Text` |
| is_required | `bool` | No | Default `False` |
| sort_order | `int` | No | Default `0` |
| is_active | `bool` | No | Default `True` |

### `AttrDefUpdate`
All fields Optional for partial update.

### `AttrDefResponse`
Extends `AuditMixin` — adds audit fields.
