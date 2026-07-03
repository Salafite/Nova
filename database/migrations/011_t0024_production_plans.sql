CREATE TABLE IF NOT EXISTS "Nova".t0024 (
    id            SERIAL PRIMARY KEY,
    business_id   INT NOT NULL REFERENCES "Nova".t0010(id) ON DELETE CASCADE,
    plan_number   VARCHAR(30) NOT NULL,
    product_id    INT REFERENCES "Nova".t0003(id) ON DELETE SET NULL,
    product_name  VARCHAR(200) NOT NULL,
    quantity      NUMERIC(12,4) NOT NULL DEFAULT 1,
    start_date    DATE,
    end_date      DATE,
    status        VARCHAR(20) NOT NULL DEFAULT 'Draft',
    notes         TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_t0024_business ON "Nova".t0024(business_id);
CREATE INDEX IF NOT EXISTS idx_t0024_plan ON "Nova".t0024(plan_number);
CREATE INDEX IF NOT EXISTS idx_t0024_active ON "Nova".t0024(is_active);
