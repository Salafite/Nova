-- Nova ERP — Digital Proof of Delivery (POD) & Mobile COD Logging Migration
-- Migration 023: Add POD signature, photo proof, COD payment tracking, and driver assignment columns to Sales Deliveries (t0077)
BEGIN;

ALTER TABLE "Nova".t0077
    ADD COLUMN IF NOT EXISTS recipient_signature TEXT,
    ADD COLUMN IF NOT EXISTS delivery_photo_url TEXT,
    ADD COLUMN IF NOT EXISTS pod_timestamp TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS delivery_location VARCHAR(255),
    ADD COLUMN IF NOT EXISTS payment_status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    ADD COLUMN IF NOT EXISTS cod_cash_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cod_check_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cod_check_number VARCHAR(100),
    ADD COLUMN IF NOT EXISTS cod_check_bank VARCHAR(100),
    ADD COLUMN IF NOT EXISTS driver_id INT REFERENCES "Nova".t0021(id);

COMMENT ON COLUMN "Nova".t0077.recipient_signature IS 'Base64 image data or URI of recipient digital signature';
COMMENT ON COLUMN "Nova".t0077.delivery_photo_url IS 'URI/URL to photo proof of delivery';
COMMENT ON COLUMN "Nova".t0077.pod_timestamp IS 'Timestamp when proof of delivery was submitted/captured';
COMMENT ON COLUMN "Nova".t0077.delivery_location IS 'GPS coordinates or delivery location description';
COMMENT ON COLUMN "Nova".t0077.payment_status IS 'COD payment status (e.g. Pending, Collected, In Transit, Reconciled)';
COMMENT ON COLUMN "Nova".t0077.cod_cash_amount IS 'Cash amount collected by driver at delivery time';
COMMENT ON COLUMN "Nova".t0077.cod_check_amount IS 'Check amount collected by driver at delivery time';
COMMENT ON COLUMN "Nova".t0077.cod_check_number IS 'Check identifier/number for COD payment';
COMMENT ON COLUMN "Nova".t0077.cod_check_bank IS 'Bank name associated with COD check payment';
COMMENT ON COLUMN "Nova".t0077.driver_id IS 'Assigned delivery driver (FK to T0021 user table)';

CREATE INDEX IF NOT EXISTS idx_t0077_driver_id ON "Nova".t0077(driver_id);
CREATE INDEX IF NOT EXISTS idx_t0077_payment_status ON "Nova".t0077(payment_status);

DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        GRANT SELECT (recipient_signature, delivery_photo_url, pod_timestamp, delivery_location, payment_status, cod_cash_amount, cod_check_amount, cod_check_number, cod_check_bank, driver_id) ON "Nova".t0077 TO nova_readonly;
    END IF;
END $$;

COMMIT;
