# Stock Movements

**Program code:** `T0064` (Stock Movements)

## Purpose
View and record stock movement history across warehouses. Each movement tracks a quantity change (positive = stock in, negative = stock out), the resulting balance, and optional reference information (e.g., sales order, purchase order).

## How to access
1. Log in to Nova ERP
2. Navigate to **Foundation > Stock Movements** in the sidebar
3. The screen loads at `#/stock-movements`

## Backing table
`Nova.T0064` — stores all stock movement records.

## API prefix
`/api/T0064I`

## Permissions
- **Full access**: Admin, Manager (can create, edit, delete)

## Dependencies
- Depends on: T0003 (Products), T0008 (Warehouses)
- Updates: T0009 (Stock Levels) via `StockMovementService`
