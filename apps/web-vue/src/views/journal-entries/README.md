# Journal Entries

**Program code:** `T0027` (Journal Entry)

## Purpose
Manage accounting journal entries — record debits and credits for financial transactions. Used by accountants to post adjusting entries, accruals, and general ledger transactions.

## How to access
1. Log in to Nova ERP
2. Navigate to **Accounting & Finance > Journal Entries** in the sidebar
3. The screen loads at `#/journal-entries`

## Backing table
`Nova.T0027` — stores all journal entry headers.

## API prefix
`/api/T0027I`

## Permissions
- **Full access**: Admin, Accountant (can create, edit, delete)
- **Read only**: Viewer (can view only)

## Dependencies
- Depends on: Chart of Accounts (T0026) for line items
- Used by: Financial Reports, Trial Balance
