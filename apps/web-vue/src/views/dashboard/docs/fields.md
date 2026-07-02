# Dashboard Fields

The dashboard displays aggregated counts, not individual record fields. There is no CRUD form.

## Stats Cards

| Metric | Source | Type |
|--------|--------|------|
| Total Products | `T0003I` response array length | Number |
| Total Customers | `T0010I` response array length | Number |
| Total Suppliers | `T0011I` response array length | Number |
| Active Orders | `T0012I` response array length | Number |
| Invoices | `T0090I` response array length | Number |
| Payments | `T0091I` response array length | Number |
| Employees | `T0030I` response array length | Number |
| Users | `T0021I` response array length | Number |

## Recent Activity

| Field | Source | Notes |
|-------|--------|-------|
| `label` | `T0090I.invoice_no` (fallback: `id`) | Display text |
| `date` | `T0090I.invoice_date` | Formatted via `toLocaleDateString()` |
