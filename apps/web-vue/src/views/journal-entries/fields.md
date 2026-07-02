# Fields — Journal Entries

## Database columns (`Nova.T0027`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| entry_date | `DATE` | Yes | — | Date of the journal entry |
| reference | `VARCHAR(100)` | No | — | External reference number |
| description | `VARCHAR(255)` | Yes | — | Description of the entry |
| status | `VARCHAR(20)` | No | `'Draft'` | Draft, Posted, or Cancelled |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### JournalEntryCreate
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| entry_date | `date` | Yes | Date of entry |
| reference | `str` | No | Max 100 chars |
| description | `str` | Yes | Max 255 chars |
| status | `str` | No | Default: `'Draft'` |

### JournalEntryUpdate
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| entry_date | `Optional[date]` | No | — |
| reference | `Optional[str]` | No | Max 100 chars |
| description | `Optional[str]` | No | Max 255 chars |
| status | `Optional[str]` | No | — |

### JournalEntryResponse
Extends `AuditMixin` — adds `created_at`, `created_by`, `updated_at`, `updated_by`, `update_number`.
