# API Endpoints — Barcodes

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0004I/` | List all barcodes | — | `BarcodeResponse[]` |
| 2 | GET | `/api/T0004I/{id}` | Get single barcode | `id` (path) | `BarcodeResponse` |
| 3 | POST | `/api/T0004I/` | Create barcode | `BarcodeCreate` body | `BarcodeResponse` |
| 4 | PUT | `/api/T0004I/{id}` | Update barcode | `id` (path) + `BarcodeUpdate` body | `BarcodeResponse` |
| 5 | DELETE | `/api/T0004I/{id}` | Delete barcode | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

**Lookup:** Product list loaded from `/api/T0003I/` for the product dropdown.
