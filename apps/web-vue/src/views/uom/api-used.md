# API Endpoints — Units of Measure

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0001I/` | List all UOMs | — | `UOMResponse[]` |
| 2 | GET | `/api/T0001I/{id}` | Get single UOM | `id` (path) | `UOMResponse` |
| 3 | POST | `/api/T0001I/` | Create a UOM | `UOMCreate` body | `UOMResponse` |
| 4 | PUT | `/api/T0001I/{id}` | Update a UOM | `id` (path) + `UOMUpdate` body | `UOMResponse` |
| 5 | DELETE | `/api/T0001I/{id}` | Delete a UOM | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`
