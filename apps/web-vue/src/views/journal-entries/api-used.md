# API Endpoints — Journal Entries

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0027I/` | List all journal entries | — | `JournalEntryResponse[]` |
| 2 | GET | `/api/T0027I/{id}` | Get single entry | `id` (path) | `JournalEntryResponse` |
| 3 | POST | `/api/T0027I/` | Create entry | `JournalEntryCreate` body | `JournalEntryResponse` |
| 4 | PUT | `/api/T0027I/{id}` | Update entry | `id` (path) + `JournalEntryUpdate` body | `JournalEntryResponse` |
| 5 | DELETE | `/api/T0027I/{id}` | Delete entry | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`
