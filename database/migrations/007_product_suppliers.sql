-- Nova ERP — Product-Supplier linking table
BEGIN;

CREATE TABLE IF NOT EXISTS "Nova".t0103 (
    id              SERIAL PRIMARY KEY,
    product_id      INT NOT NULL REFERENCES "Nova".t0003(id) ON DELETE CASCADE,
    supplier_id     INT NOT NULL REFERENCES "Nova".t0011(id) ON DELETE CASCADE,
    supplier_sku    VARCHAR(100),
    unit_cost       NUMERIC(12,2) DEFAULT 0,
    lead_time_days  INT DEFAULT 0,
    is_preferred    BOOLEAN NOT NULL DEFAULT false,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1,
    UNIQUE(product_id, supplier_id)
);
COMMENT ON TABLE "Nova".t0103 IS 'Product-Supplier linking';
CREATE INDEX IF NOT EXISTS idx_t0103_product_id ON "Nova".t0103(product_id);
CREATE INDEX IF NOT EXISTS idx_t0103_supplier_id ON "Nova".t0103(supplier_id);

COMMIT;
