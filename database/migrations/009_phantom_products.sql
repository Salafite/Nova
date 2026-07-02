-- Nova ERP — Phantom product detection columns
BEGIN;

ALTER TABLE "Nova".t0003
  ADD COLUMN IF NOT EXISTS is_phantom BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS last_transaction_date TIMESTAMPTZ;

COMMENT ON COLUMN "Nova".t0003.is_phantom IS 'Flagged as phantom (no orders in 12+ months)';
COMMENT ON COLUMN "Nova".t0003.last_transaction_date IS 'Date of last order/invoice transaction';

COMMIT;
