CREATE TABLE IF NOT EXISTS "Nova".t0105 (
    id            SERIAL PRIMARY KEY,
    business_id   INT NOT NULL REFERENCES "Nova".t0010(id) ON DELETE CASCADE,
    count_number  VARCHAR(30) NOT NULL,
    warehouse_id  INT REFERENCES "Nova".t0008(id) ON DELETE SET NULL,
    count_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    status        VARCHAR(20) NOT NULL DEFAULT 'Draft',
    notes         TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0106 (
    id            SERIAL PRIMARY KEY,
    count_id      INT NOT NULL REFERENCES "Nova".t0105(id) ON DELETE CASCADE,
    product_id    INT NOT NULL REFERENCES "Nova".t0003(id) ON DELETE CASCADE,
    expected_qty  NUMERIC(12,4) NOT NULL DEFAULT 0,
    counted_qty   NUMERIC(12,4),
    notes         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_t0105_business ON "Nova".t0105(business_id);
CREATE INDEX IF NOT EXISTS idx_t0105_status ON "Nova".t0105(status);
CREATE INDEX IF NOT EXISTS idx_t0106_count ON "Nova".t0106(count_id);
CREATE INDEX IF NOT EXISTS idx_t0106_product ON "Nova".t0106(product_id);
