# API Endpoints — UOM Conversions

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0002I/` | List all conversions | — | `UOMConvResponse[]` |
| 2 | GET | `/api/T0002I/{id}` | Get single conversion | `id` (path) | `UOMConvResponse` |
| 3 | POST | `/api/T0002I/` | Create conversion | `UOMConvCreate` body | `UOMConvResponse` |
| 4 | PUT | `/api/T0002I/{id}` | Update conversion | `id` (path) + `UOMConvUpdate` body | `UOMConvResponse` |
| 5 | DELETE | `/api/T0002I/{id}` | Delete conversion | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

**Lookup:** UOM list loaded from `/api/T0001I/` for the from/to UOM dropdowns.
