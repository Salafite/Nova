# API Endpoints — Attributes

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0005I/` | List all attributes | — | `AttrDefResponse[]` |
| 2 | GET | `/api/T0005I/{id}` | Get single attribute | `id` (path) | `AttrDefResponse` |
| 3 | POST | `/api/T0005I/` | Create attribute | `AttrDefCreate` body | `AttrDefResponse` |
| 4 | PUT | `/api/T0005I/{id}` | Update attribute | `id` (path) + `AttrDefUpdate` body | `AttrDefResponse` |
| 5 | DELETE | `/api/T0005I/{id}` | Delete attribute | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`
