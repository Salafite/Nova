-- Nova ERP — Pick List tables for order fulfillment
BEGIN;

CREATE TABLE IF NOT EXISTS "Nova".t0101 (
    id              SERIAL PRIMARY KEY,
    pick_list_number VARCHAR(50) NOT NULL UNIQUE,
    sales_order_id  INT NOT NULL REFERENCES "Nova".t0012(id),
    warehouse_id    INT REFERENCES "Nova".t0008(id),
    status          VARCHAR(30) NOT NULL DEFAULT 'Pending',
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0101 IS 'Pick Lists — generated from confirmed sales orders';
COMMENT ON COLUMN "Nova".t0101.status IS 'Pending | In Progress | Completed | Cancelled';
CREATE INDEX IF NOT EXISTS idx_t0101_sales_order_id ON "Nova".t0101(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_t0101_status ON "Nova".t0101(status);

CREATE TABLE IF NOT EXISTS "Nova".t0102 (
    id                SERIAL PRIMARY KEY,
    pick_list_id      INT NOT NULL REFERENCES "Nova".t0101(id) ON DELETE CASCADE,
    sales_order_line_id INT REFERENCES "Nova".t0013(id),
    product_id        INT NOT NULL,
    product_name      VARCHAR(200),
    qty_ordered       NUMERIC(12,2) NOT NULL DEFAULT 0,
    qty_picked        NUMERIC(12,2) NOT NULL DEFAULT 0,
    line_number       INT NOT NULL DEFAULT 1,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by        INT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by        INT,
    update_number     INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0102 IS 'Pick List Items';
COMMENT ON COLUMN "Nova".t0102.qty_picked IS 'Quantity actually picked so far';
CREATE INDEX IF NOT EXISTS idx_t0102_pick_list_id ON "Nova".t0102(pick_list_id);
CREATE INDEX IF NOT EXISTS idx_t0102_product_id ON "Nova".t0102(product_id);

COMMIT;
