# API Endpoints — Purchase Orders

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0014I/` | List all purchase orders | — | `PurchaseOrderResponse[]` |
| 2 | GET | `/api/T0014I/{id}` | Get single PO | `id` (path) | `PurchaseOrderResponse` |
| 3 | POST | `/api/T0014I/` | Create PO | `PurchaseOrderCreate` body | `PurchaseOrderResponse` |
| 4 | PUT | `/api/T0014I/{id}` | Update PO | `id` (path) + `PurchaseOrderUpdate` body | `PurchaseOrderResponse` |
| 5 | DELETE | `/api/T0014I/{id}` | Delete PO | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

**Lookup:** Suppliers loaded from `/api/T0011I/` for supplier dropdown.
