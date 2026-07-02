# Products

**Program code:** `T0003` — Products

## Purpose
Manage the product catalog — define product names, SKUs, pricing, categories, brands, and tax rates. Products are the core entity used across inventory, sales, purchasing, and manufacturing.

## How to access
1. Log in to Nova ERP
2. Navigate to **Foundation > Products** in the sidebar
3. The screen loads at `#/products`

## Backing table
`Nova.T0003` — stores all product records.

## API prefix
`/api/T0003I`

## Permissions
- **Full access**: Admin, Inventory Manager (can create, edit, delete)
- **Read only**: Viewer (can view only)

## Dependencies
- Depends on: None (standalone core entity)
- Used by: Inventory (T0009), Barcodes (T0004), Stock Movements (T0064), Sales Orders (T0012), Purchase Orders (T0014)
