# Barcodes

**Program code:** `T0004` (Barcodes)

## Purpose
Manage product barcodes for scanning and identification. Supports multiple barcode types (EAN13, EAN8, UPC, CODE128, QR) and allows marking one barcode per product as primary.

## How to access
1. Log in to Nova ERP
2. Navigate to **Foundation > Barcodes** in the sidebar
3. The screen loads at `#/barcodes`

## Backing table
`Nova.T0004` — stores all product barcode records.

## API prefix
`/api/T0004I`

## Permissions
- **Full access**: Admin, Manager (can create, edit, delete)
- **Read only**: Viewer (can view only)

## Dependencies
- Depends on: T0003 (Products)
