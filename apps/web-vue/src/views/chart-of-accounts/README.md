# Chart of Accounts

**Program code:** `T0026` — Chart of Accounts

## Purpose
Manage the organization's chart of accounts, including account codes, names, types (Asset, Liability, Equity, Revenue, Expense), and currency settings. Used by the finance team to define the financial structure.

## How to access
1. Log in to Nova ERP
2. Navigate to **Accounting & Finance > Chart of Accounts** in the sidebar
3. The screen loads at `#/chart-of-accounts`

## Backing table
`Nova.T0026` — stores all COA account records.

## API prefix
`/api/T0026I`

## Permissions
- **Full access**: Admin, Manager (can create, edit, delete)
- **Read only**: Viewer (can view only)

## Dependencies
- Depends on: none
- Used by: Journal Entries, Invoices
