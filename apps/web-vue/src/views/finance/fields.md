# Fields — Invoices

## Database columns (`Nova.T0090`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| invoice_number | `VARCHAR(50)` | Yes | — | Unique invoice number |
| invoice_type | `VARCHAR(10)` | Yes | Sales | Sales or Purchase |
| partner_id | `INT` | Yes | — | Customer or Supplier ID |
| issue_date | `DATE` | Yes | — | Invoice issue date |
| due_date | `DATE` | Yes | — | Payment due date |
| total_amount | `DECIMAL` | Yes | — | Total invoice amount |
| status | `VARCHAR(20)` | No | Draft | Draft, Unpaid, Paid, Cancelled |

## Pydantic models

### `InvoiceCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| invoice_number | `str` | Yes | Max 50 |
| invoice_type | `str` | No | Sales or Purchase |
| partner_id | `int` | Yes | — |
| issue_date | `date` | Yes | — |
| due_date | `date` | Yes | — |
| total_amount | `float` | Yes | >= 0 |
| status | `str` | No | Default Draft |

### `InvoiceUpdate`
All fields Optional.

### `InvoiceResponse`
Extends `AuditMixin`.
