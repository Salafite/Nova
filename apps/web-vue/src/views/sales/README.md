# Sales Orders

**Program code:** `T0012` (Sales Orders)

## Purpose
Manage sales orders from customers. Track order status, amounts, and dates. Sales orders flow into inventory and receivables.

## How to access
1. Log in to Nova ERP
2. Navigate to **CRM & Procurement > Sales** in the sidebar
3. The screen loads at `#/sales`

## Backing table
`Nova.T0012` — stores all sales order records.

## API prefix
`/api/T0012I`

## Permissions
- **Full access**: Admin, Sales Rep (can create, edit, delete)
- **Read only**: Viewer (can view only)

## Dependencies
- Depends on: T0010 (Customers)
- Contains: T0013 (Sales Order Lines)
