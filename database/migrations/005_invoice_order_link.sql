-- Nova ERP — Link invoices to sales orders for auto-creation on delivery
BEGIN;

ALTER TABLE "Nova".t0090 ADD COLUMN IF NOT EXISTS sales_order_id INT REFERENCES "Nova".t0012(id);
ALTER TABLE "Nova".t0090 ALTER COLUMN status SET DEFAULT 'Unpaid';

COMMENT ON COLUMN "Nova".t0090.sales_order_id IS 'Sales order that generated this invoice';
CREATE INDEX IF NOT EXISTS idx_t0090_sales_order_id ON "Nova".t0090(sales_order_id);

COMMIT;
