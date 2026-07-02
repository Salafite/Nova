# Customers

**Program code:** `T0010` (Customers)

## Purpose
Manage customer accounts including contact info, credit limits, and current balances. Used by sales orders and receivables.

## How to access
1. Log in to Nova ERP
2. Navigate to **CRM & Procurement > Customers** in the sidebar
3. The screen loads at `#/customers`

## Backing table
`Nova.T0010` — stores all customer records.

## API prefix
`/api/T0010I`

## Permissions
- **Full access**: Admin, Sales Rep (can create, edit, delete)
- **Read only**: Viewer (can view only)

## Dependencies
- Referenced by: T0012 (Sales Orders)
