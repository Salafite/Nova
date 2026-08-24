-- Nova ERP — Catch-Weight & Dual Unit-of-Measure (UOM) Pricing Engine
-- Migration 021: Dual UOM Configuration, Scale Weight Tracking & Catch-Weight Invoicing
BEGIN;

-- 1. Master Data Products (t0003): Add Dual UOM & Catch-Weight Configuration
ALTER TABLE "Nova".t0003
    ADD COLUMN IF NOT EXISTS is_catch_weight BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS pricing_uom_id INT REFERENCES "Nova".t0001(id),
    ADD COLUMN IF NOT EXISTS nominal_weight NUMERIC(12,4) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS tolerance_pct NUMERIC(6,2) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS pricing_basis VARCHAR(20) DEFAULT 'weight';

COMMENT ON COLUMN "Nova".t0003.is_catch_weight IS 'Flag indicating product is sold/priced by catch-weight (variable physical weight)';
COMMENT ON COLUMN "Nova".t0003.pricing_uom_id IS 'Unit of Measure used for pricing/billing (e.g. Kilograms, Pounds)';
COMMENT ON COLUMN "Nova".t0003.nominal_weight IS 'Expected nominal weight per stocking unit (e.g. kg per case)';
COMMENT ON COLUMN "Nova".t0003.tolerance_pct IS 'Allowable weight variance percentage (+/- %) without requiring supervisor approval';
COMMENT ON COLUMN "Nova".t0003.pricing_basis IS 'Pricing basis: weight (actual weighed amount) or unit (fixed per piece/case)';

CREATE INDEX IF NOT EXISTS idx_t0003_is_catch_weight ON "Nova".t0003(is_catch_weight);
CREATE INDEX IF NOT EXISTS idx_t0003_pricing_uom_id ON "Nova".t0003(pricing_uom_id);

-- 2. Product UOM Conversions (t0007): Add Dual UOM Attributes
ALTER TABLE "Nova".t0007
    ADD COLUMN IF NOT EXISTS is_catch_weight BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS pricing_uom_id INT REFERENCES "Nova".t0001(id),
    ADD COLUMN IF NOT EXISTS nominal_weight NUMERIC(12,4) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS tolerance_pct NUMERIC(6,2) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS pricing_basis VARCHAR(20) DEFAULT 'weight';

COMMENT ON COLUMN "Nova".t0007.is_catch_weight IS 'Flag indicating dual UOM catch-weight applies to this product UOM configuration';
COMMENT ON COLUMN "Nova".t0007.pricing_uom_id IS 'Pricing unit of measure reference';
COMMENT ON COLUMN "Nova".t0007.nominal_weight IS 'Nominal weight per stocking unit';
COMMENT ON COLUMN "Nova".t0007.tolerance_pct IS 'Tolerance percentage (+/-)';
COMMENT ON COLUMN "Nova".t0007.pricing_basis IS 'Pricing basis: weight or unit';

-- 3. Warehouse Pick List Items (t0102): Scale Weight Capture & Tolerance Discrepancy Approvals
ALTER TABLE "Nova".t0102
    ADD COLUMN IF NOT EXISTS catch_weight_actual NUMERIC(12,4) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS catch_weight_uom VARCHAR(50) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS nominal_weight NUMERIC(12,4) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS tolerance_pct NUMERIC(6,2) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS tolerance_variance_pct NUMERIC(6,2) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS tolerance_status VARCHAR(30) DEFAULT 'Not Applicable',
    ADD COLUMN IF NOT EXISTS supervisor_approved BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS supervisor_approved_by INT REFERENCES "Nova".t0021(id),
    ADD COLUMN IF NOT EXISTS supervisor_approved_at TIMESTAMPTZ DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS supervisor_notes TEXT DEFAULT NULL;

COMMENT ON COLUMN "Nova".t0102.catch_weight_actual IS 'Actual physical scale weight measured during warehouse picking';
COMMENT ON COLUMN "Nova".t0102.catch_weight_uom IS 'Unit of measure for the actual scale weight (e.g. kg, lbs)';
COMMENT ON COLUMN "Nova".t0102.nominal_weight IS 'Nominal expected weight for the picked quantity';
COMMENT ON COLUMN "Nova".t0102.tolerance_pct IS 'Allowed tolerance percentage (+/-) from nominal weight';
COMMENT ON COLUMN "Nova".t0102.tolerance_variance_pct IS 'Actual weight variance percentage vs nominal';
COMMENT ON COLUMN "Nova".t0102.tolerance_status IS 'Status: Within Tolerance | Out of Tolerance | Approved | Pending Approval | Not Applicable';
COMMENT ON COLUMN "Nova".t0102.supervisor_approved IS 'Whether out-of-tolerance discrepancy was approved by a supervisor';
COMMENT ON COLUMN "Nova".t0102.supervisor_approved_by IS 'Supervisor user who approved tolerance variance';
COMMENT ON COLUMN "Nova".t0102.supervisor_approved_at IS 'Timestamp of supervisor approval';
COMMENT ON COLUMN "Nova".t0102.supervisor_notes IS 'Supervisor comments/reasons on approval';

CREATE INDEX IF NOT EXISTS idx_t0102_tolerance_status ON "Nova".t0102(tolerance_status);
CREATE INDEX IF NOT EXISTS idx_t0102_supervisor_approved ON "Nova".t0102(supervisor_approved);

-- 4. Sales Order Lines (t0013): Dual UOM Pricing & Catch-Weight Recalculation
ALTER TABLE "Nova".t0013
    ADD COLUMN IF NOT EXISTS is_catch_weight BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS pricing_uom_id INT REFERENCES "Nova".t0001(id),
    ADD COLUMN IF NOT EXISTS unit_price_pricing_uom NUMERIC(12,4) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS nominal_weight NUMERIC(12,4) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS catch_weight_actual NUMERIC(12,4) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS recalculated_total NUMERIC(12,2) DEFAULT NULL;

COMMENT ON COLUMN "Nova".t0013.is_catch_weight IS 'Flag indicating order line uses catch-weight pricing';
COMMENT ON COLUMN "Nova".t0013.pricing_uom_id IS 'Pricing unit of measure (e.g. kg)';
COMMENT ON COLUMN "Nova".t0013.unit_price_pricing_uom IS 'Price per pricing UOM unit (e.g. price per kg)';
COMMENT ON COLUMN "Nova".t0013.nominal_weight IS 'Nominal weight for ordered quantity';
COMMENT ON COLUMN "Nova".t0013.catch_weight_actual IS 'Actual weighed catch weight from warehouse fulfillment';
COMMENT ON COLUMN "Nova".t0013.recalculated_total IS 'Final recalculated line total based on actual catch-weight';

CREATE INDEX IF NOT EXISTS idx_t0013_pricing_uom_id ON "Nova".t0013(pricing_uom_id);

-- 5. Invoices (t0090): Dual UOM Catch-Weight Aggregates & Adjustments
ALTER TABLE "Nova".t0090
    ADD COLUMN IF NOT EXISTS is_catch_weight BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS nominal_total_weight NUMERIC(12,4) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS actual_total_weight NUMERIC(12,4) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS weight_adjustment_amount NUMERIC(12,2) NOT NULL DEFAULT 0;

COMMENT ON COLUMN "Nova".t0090.is_catch_weight IS 'Flag indicating invoice contains catch-weight products';
COMMENT ON COLUMN "Nova".t0090.nominal_total_weight IS 'Total nominal weight across invoiced catch-weight items';
COMMENT ON COLUMN "Nova".t0090.actual_total_weight IS 'Total actual scale weight across invoiced catch-weight items';
COMMENT ON COLUMN "Nova".t0090.weight_adjustment_amount IS 'Net financial adjustment due to catch-weight variance vs nominal';

COMMIT;
