-- Nova ERP — Add reserved_qty to stock levels for order reservation
BEGIN;

ALTER TABLE "Nova".t0009 ADD COLUMN IF NOT EXISTS reserved_qty NUMERIC(12,2) NOT NULL DEFAULT 0;

ALTER TABLE "Nova".t0012 ADD COLUMN IF NOT EXISTS warehouse_id INT REFERENCES "Nova".t0008(id);

COMMENT ON COLUMN "Nova".t0009.reserved_qty IS 'Quantity reserved by confirmed orders';
COMMENT ON COLUMN "Nova".t0012.warehouse_id IS 'Warehouse for stock reservation';

CREATE INDEX IF NOT EXISTS idx_t0009_reserved_qty ON "Nova".t0009(reserved_qty);

COMMIT;
