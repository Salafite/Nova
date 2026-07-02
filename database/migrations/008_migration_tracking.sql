-- Nova ERP — Migration batch tracking for CSV import rollback
BEGIN;

CREATE TABLE IF NOT EXISTS "Nova".t0104 (
    id              SERIAL PRIMARY KEY,
    batch_key       VARCHAR(64) NOT NULL UNIQUE,
    entity_type     VARCHAR(30) NOT NULL,
    total_rows      INT NOT NULL DEFAULT 0,
    inserted_rows   INT NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'Preview',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0104 IS 'Migration batches for tracking CSV imports';
COMMENT ON COLUMN "Nova".t0104.status IS 'Preview | Committed | RolledBack';
CREATE INDEX IF NOT EXISTS idx_t0104_batch_key ON "Nova".t0104(batch_key);

COMMIT;
