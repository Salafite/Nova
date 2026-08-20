-- Nova ERP — Batch Tracking & FEFO Warehouse Picking Migration
BEGIN;

-- 1. Add batch tracking columns to Goods Receipt Lines (t0076)
ALTER TABLE "Nova".t0076
    ADD COLUMN IF NOT EXISTS batch_number VARCHAR(255),
    ADD COLUMN IF NOT EXISTS manufacturing_date DATE,
    ADD COLUMN IF NOT EXISTS expiry_date DATE;

COMMENT ON COLUMN "Nova".t0076.batch_number IS 'Batch or lot number captured at goods receipt';
COMMENT ON COLUMN "Nova".t0076.manufacturing_date IS 'Manufacturing / production date';
COMMENT ON COLUMN "Nova".t0076.expiry_date IS 'Expiration date';

CREATE INDEX IF NOT EXISTS idx_t0076_batch_number ON "Nova".t0076(batch_number);
CREATE INDEX IF NOT EXISTS idx_t0076_expiry_date ON "Nova".t0076(expiry_date);

-- 2. Add batch allocation and override columns to Pick List Items (t0102)
ALTER TABLE "Nova".t0102
    ADD COLUMN IF NOT EXISTS batch_id INT REFERENCES "Nova".t0088(id),
    ADD COLUMN IF NOT EXISTS batch_number VARCHAR(255),
    ADD COLUMN IF NOT EXISTS expiry_date DATE,
    ADD COLUMN IF NOT EXISTS picked_batch_id INT REFERENCES "Nova".t0088(id),
    ADD COLUMN IF NOT EXISTS picked_batch_number VARCHAR(255);

COMMENT ON COLUMN "Nova".t0102.batch_id IS 'Suggested lot ID allocated by FEFO engine';
COMMENT ON COLUMN "Nova".t0102.batch_number IS 'Suggested lot number';
COMMENT ON COLUMN "Nova".t0102.expiry_date IS 'Expiration date of suggested lot';
COMMENT ON COLUMN "Nova".t0102.picked_batch_id IS 'Actual picked lot ID (if different from suggested)';
COMMENT ON COLUMN "Nova".t0102.picked_batch_number IS 'Actual picked lot number';

CREATE INDEX IF NOT EXISTS idx_t0102_batch_id ON "Nova".t0102(batch_id);
CREATE INDEX IF NOT EXISTS idx_t0102_picked_batch_id ON "Nova".t0102(picked_batch_id);
CREATE INDEX IF NOT EXISTS idx_t0102_batch_number ON "Nova".t0102(batch_number);

COMMIT;
