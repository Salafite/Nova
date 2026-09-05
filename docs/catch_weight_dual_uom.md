# Catch Weight & Dual Unit of Measure (UoM) Architecture & User Guide

Nova ERP provides native end-to-end support for **Dual Unit of Measure (Dual UoM)** and **Catch Weight** management designed specifically for the food & beverage, meat, cheese, seafood, and perishable distribution industries.

---

## 1. Overview & Business Rationale

In perishable food distribution, products are frequently purchased, stored, or ordered by discrete units (e.g. cases, boxes, wheels, cuts), but priced and billed based on exact scale weight (e.g. kilograms, pounds). Because individual natural items vary in mass:
- A customer orders **5 wheels** of Parmigiano Reggiano (ordered in inventory UOM: Units / Wheels).
- Nominal catalogue weight is **40.0 kg per wheel** (total nominal: 200.0 kg).
- Unit price is **.00 per kg** (pricing UOM: KG).
- When picked in the warehouse and weighed on certified scales, the actual weight is **194.5 kg**.
- If billed by nominal weight (,000.00), the customer is overcharged; if billed incorrectly, margins are lost.

With Nova ERP's Catch Weight subsystem:
1. Exact scale weights are captured or scanned (GS1-128 / AI 310x barcodes) during warehouse pick list fulfillment.
2. Built-in tolerance rules automatically flag variances outside allowed thresholds (e.g. ±10%) and enforce supervisor authorization gates before shipment.
3. Sales order lines, subtotals, taxes, and final invoices are automatically recalculated against actual scale weights.
4. The inventory stock ledger maintains simultaneous dual balances: discrete package count and aggregate net weight.

---

## 2. Core Concepts & Data Model

### 2.1 Configuration Attributes

| Field | Description | Example |
|---|---|---|
| `is_catch_weight` | Boolean flag indicating whether actual scale weight is required at fulfillment. | `true` |
| `pricing_uom_id` | Foreign key referencing the unit of measure used for billing calculations (T0001). | `2` (KG) |
| `nominal_weight` | Expected/average weight per single unit in the product's primary inventory UOM. | `5.00` |
| `tolerance_pct` | Maximum acceptable variance percentage before supervisor approval is mandated. | `10.0` (±10%) |
| `pricing_basis` | Calculation mode: `'weight'` (billed on scale weight) or `'nominal'` (billed on standard weight). | `'weight'` |

### 2.2 Database Schema Alignment

`
┌───────────────────────────┐          ┌──────────────────────────┐
│   T0003 Product Master    │          │  T0007 UOM Conversions   │
├───────────────────────────┤          ├──────────────────────────┤
│ is_catch_weight (BOOL)    │          │ is_catch_weight (BOOL)   │
│ pricing_uom_id (INT FK)   │          │ pricing_uom_id (INT FK)  │
│ nominal_weight (NUMERIC)  │          │ nominal_weight (NUMERIC) │
│ tolerance_pct (NUMERIC)   │          │ tolerance_pct (NUMERIC)  │
│ pricing_basis (VARCHAR)   │          │ pricing_basis (VARCHAR)  │
└─────────────┬─────────────┘          └──────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 T0102 Warehouse Pick List Items                 │
├─────────────────────────────────────────────────────────────────┤
│ catch_weight_actual (NUMERIC)  - Scale weight recorded          │
│ catch_weight_uom (VARCHAR)     - UOM of recorded scale weight   │
│ nominal_weight (NUMERIC)       - Expected aggregate weight      │
│ tolerance_pct (NUMERIC)        - Allowed tolerance threshold    │
│ tolerance_variance_pct (NUM)   - Calculated variance percentage │
│ tolerance_status (VARCHAR)     - Within / Out of Tolerance      │
│ supervisor_approved (BOOL)     - Authorization status           │
│ supervisor_approved_by (INT)   - Supervisor user ID             │
│ supervisor_approved_at (TS)    - Authorization timestamp        │
│ supervisor_notes (TEXT)        - Justification audit note       │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    T0013 Sales Order Lines                      │
├─────────────────────────────────────────────────────────────────┤
│ is_catch_weight (BOOL)         - Catch weight line indicator    │
│ pricing_uom_id (INT FK)        - Billing unit of measure        │
│ unit_price_pricing_uom (NUM)   - Price per kg / lb              │
│ nominal_weight (NUMERIC)       - Nominal expected line weight   │
│ catch_weight_actual (NUMERIC)  - Picked scale weight            │
│ recalculated_total (NUMERIC)   - Final line total from weight   │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      T0090 Sales Invoices                       │
├─────────────────────────────────────────────────────────────────┤
│ is_catch_weight (BOOL)         - Has catch weight adjustments   │
│ nominal_total_weight (NUMERIC) - Aggregate nominal weight       │
│ actual_total_weight (NUMERIC)  - Aggregate scale weight picked  │
│ weight_adjustment_amount (NUM) - Net financial adjustment       │
└─────────────────────────────────────────────────────────────────┘
`

---

## 3. Warehouse Fulfillment & Scale Weight Capture

### 3.1 Pick Workflow

1. **Order Confirmation & Pick List Generation**: When a sales order is confirmed, pick list items (T0102) inherit catch-weight settings, pricing UOM, nominal weight, and tolerance percentage from the product master.
2. **Weighing & Scanning**:
   - **Scale Entry**: The picker places the item on the scale and enters the actual weight (e.g. 24.2 kg for 5 boxes with 25.0 kg nominal).
   - **GS1-128 Barcode Scanning**: The system decodes GS1 barcodes with Application Identifier 310x (net weight in kilograms) or variable weight EAN/UPC barcodes, automatically extracting product SKU and weight.
3. **Tolerance Evaluation**:
   - Variance formula: Variance % = ((Actual Weight - Nominal Weight) / Nominal Weight) * 100
   - If |Variance %| <= Tolerance %, status is set to 'Within Tolerance' (supervisor_approved = true).
   - If |Variance %| > Tolerance %, status is set to 'Out of Tolerance' (supervisor_approved = false).

### 3.2 Supervisor Approval Gate

- **Completion Gate**: PickListService.complete_picking() checks for unapproved 'Out of Tolerance' items. If found, pick list completion is blocked (HTTP 400).
- **Delivery Gate**: SalesOrderService.deliver_order() validates all linked pick lists. If any item has unapproved discrepancies, dispatch and delivery are blocked (HTTP 400).
- **Approval API**: Supervisors review discrepancies via GET /api/T0101I/{id}/discrepancies and approve with audit comments via POST /api/T0101I/{id}/approve-tolerance.

---

## 4. Invoicing & Dynamic Repricing Engine

### 4.1 Calculation Formulas

For catch-weight items priced on actual weight:

1. **Line Total Recalculation**:
   - Recalculated Line Total = catch_weight_actual * unit_price_pricing_uom (or pro-rated effective price rate unit_price / nominal_weight).

2. **Order Subtotal & Financial Adjustment**:
   - Recalculated Subtotal = Sum(Recalculated Line Totals) + Sum(Standard Line Totals)
   - Weight Adjustment Amount = Recalculated Subtotal - Original Subtotal

3. **Taxes & Grand Total**:
   - Recalculated Tax = Recalculated Subtotal * Effective Tax Rate
   - Recalculated Total = Recalculated Subtotal + Recalculated Tax

4. **Invoice Generation**:
   The final invoice (T0090) itemizes:
   - Ordered package count & pricing UOM
   - Nominal total weight vs Actual picked scale weight
   - Net weight adjustment credit / debit amount
   - Exact per-line weight breakdown

---

## 5. Dual-Balance Stock Ledger

The stock movement ledger (T0064) records both:
- quantity: Discrete package count (e.g. -5 boxes).
- weight: Net physical scale weight (e.g. -24.2 kg).

Inventory queries provide simultaneous visibility into:
- Discrete Units on Hand (for warehouse slotting and pack counting).
- Net Weight on Hand (for accurate balance-sheet valuation and yield tracking).

---

## 6. REST API Reference

### Products & UOM
- GET /api/T0003I & POST /api/T0003I: Product master CRUD with is_catch_weight, pricing_uom_id, 
ominal_weight, 	olerance_pct, pricing_basis.
- GET /api/T0007I & POST /api/T0007I: Product UOM conversions with catch-weight attributes.

### Warehouse Pick Lists
- POST /api/T0101I/{id}/pick-item/{item_id}: Record picked quantity and scale weight (catch_weight_actual, catch_weight_uom).
- GET /api/T0101I/{id}/discrepancies: Retrieve list of unapproved out-of-tolerance lines.
- POST /api/T0101I/{id}/approve-tolerance: Supervisor approval for out-of-tolerance items.
- POST /api/T0101I/{id}/items/{item_id}/approve-tolerance: Single-item supervisor approval.

### Sales Orders & Deliveries
- GET /api/T0012I/{id}/recalculate-preview: Preview repriced order lines and weight adjustment amount.
- POST /api/T0012I/{id}/recalculate: Persist catch-weight recalculation to order and lines.
- POST /api/T0012I/{id}/deliver: Enforces discrepancy approval gate and automatically applies scale weights.

### Invoices
- GET /api/T0090I/{id}/catch-weight-breakdown: Retrieve nominal vs actual weights and line-by-line financial adjustments.

---

## 7. Model Context Protocol (MCP) AI Tools

AI agents (e.g. Claude Code, In-App Assistant) interact with catch-weight operations via the following MCP tools:

| MCP Server | Tool Name | Description |
|---|---|---|
| inventory | create_product / update_product | Configure catch-weight parameters (is_catch_weight, 
ominal_weight, 	olerance_pct, pricing_basis). |
| inventory | list_products | Filter and inspect catch-weight configurations across the catalogue. |
| warehouse | pick_item | Record picked item scale weight (catch_weight_actual, catch_weight_uom). |
| warehouse | check_pick_list_discrepancies | Audit pending out-of-tolerance items requiring approval. |
| warehouse | pprove_pick_tolerance | Supervisor authorization tool with required justification notes. |
| sales | 
ecalculate_order_catch_weight | AI tool to preview and recalculate sales order totals based on picked weights. |
| sales | create_order / create_order_line | Create dual-UOM sales lines with pricing UOM and nominal weight specifications. |
