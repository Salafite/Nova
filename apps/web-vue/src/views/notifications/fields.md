# Fields — User Notifications

## Database columns (`Nova.T0098`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| user_id | `INT` | Yes | — | Foreign key to T0021 (System Users) |
| title | `VARCHAR(200)` | Yes | — | Notification title |
| message | `TEXT` | No | `NULL` | Notification body text |
| notification_type | `VARCHAR(20)` | No | `'Info'` | Type: Info, Warning, Error, Success |
| reference_type | `VARCHAR(30)` | No | `NULL` | Related entity type (e.g. sales_order) |
| reference_id | `INT` | No | `NULL` | Related entity ID |
| is_read | `BOOLEAN` | No | `FALSE` | Whether the notification has been read |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit — creation timestamp |

## Pydantic models

### `NotificationCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| user_id | `int` | Yes | Target user |
| title | `str` | Yes | Max 200 chars |
| message | `Optional[str]` | No | Free text body |
| notification_type | `str` | No | Default: `'Info'` |
| reference_type | `Optional[str]` | No | Max 30 chars |
| reference_id | `Optional[int]` | No | — |

### `NotificationUpdate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| is_read | `Optional[bool]` | No | Toggle read status |

### `NotificationResponse`
| Field | Type | Notes |
|-------|------|-------|
| id | `int` | Primary key |
| user_id | `int` | — |
| title | `str` | — |
| message | `Optional[str]` | — |
| notification_type | `str` | — |
| reference_type | `Optional[str]` | — |
| reference_id | `Optional[int]` | — |
| is_read | `bool` | — |
| created_at | `Optional[datetime]` | Audit timestamp |
