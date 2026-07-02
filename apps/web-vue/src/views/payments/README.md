# Payments

**Program code:** `T0091` (Payment)

## Purpose
Record payments received from customers or made to suppliers. Supports multiple payment methods (Cash, Bank Transfer, Card) and tracks payment status.

## How to access
1. Log in to Nova ERP
2. Navigate to **Accounting & Finance > Payments** in the sidebar
3. The screen loads at `#/payments`

## Backing table
`Nova.T0091` — stores all payment records.

## API prefix
`/api/T0091I`

## Permissions
- **Full access**: Admin, Accountant (can create, edit, delete)
- **Read only**: Viewer (can view only)

## Dependencies
- Depends on: Invoices (T0090), Customers (T0010), Suppliers (T0011)
- Used by: Account Reconciliation, Cash Flow Reports
