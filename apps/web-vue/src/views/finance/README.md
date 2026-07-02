# Invoices

**Program code:** `T0090` — Invoices

## Purpose
Manage sales and purchase invoices, including invoice numbers, partner details, issue/due dates, amounts, and status tracking.

## How to access
1. Log in to Nova ERP
2. Navigate to **Accounting & Finance > Invoices** in the sidebar
3. The screen loads at `#/finance`

## Backing table
`Nova.T0090` — stores all invoice records.

## API prefix
`/api/T0090I`

## Permissions
- **Full access**: Admin, Manager
- **Read only**: Viewer

## Dependencies
- Depends on: Partners (Customers/Suppliers), Payment Terms
- Used by: Payments
