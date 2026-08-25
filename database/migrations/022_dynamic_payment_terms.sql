-- Nova ERP — Dynamic Payment Terms & Automated Due Date Engine
-- Migration 022: Payment terms linkage and early discount metadata on Invoices (t0090)
BEGIN;

-- 1. Invoices (t0090): Add Payment Term & Early Payment Discount Columns
ALTER TABLE "Nova".t0090
    ADD COLUMN IF NOT EXISTS payment_term_id INT REFERENCES "Nova".t0096(id),
    ADD COLUMN IF NOT EXISTS discount_due_date DATE DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS discount_percentage NUMERIC(5,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS discount_days INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS early_discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0;

COMMENT ON COLUMN "Nova".t0090.payment_term_id IS 'Assigned payment term identifier (FK to T0096)';
COMMENT ON COLUMN "Nova".t0090.discount_due_date IS 'Cutoff date for early payment discount eligibility';
COMMENT ON COLUMN "Nova".t0090.discount_percentage IS 'Early payment discount percentage applicable before cutoff';
COMMENT ON COLUMN "Nova".t0090.discount_days IS 'Number of days within which early payment discount is valid';
COMMENT ON COLUMN "Nova".t0090.early_discount_amount IS 'Calculated maximum early discount amount if paid within discount period';

-- Indexes for fast lookup and aging analysis
CREATE INDEX IF NOT EXISTS idx_t0090_payment_term_id ON "Nova".t0090(payment_term_id);
CREATE INDEX IF NOT EXISTS idx_t0090_discount_due_date ON "Nova".t0090(discount_due_date);
CREATE INDEX IF NOT EXISTS idx_t0090_due_date ON "Nova".t0090(due_date);

-- 2. Ensure Payment Term FK and indexes on Customers (t0010) and Sales Orders (t0012)
CREATE INDEX IF NOT EXISTS idx_t0010_payment_term_id ON "Nova".t0010(payment_term_id);
CREATE INDEX IF NOT EXISTS idx_t0012_payment_term_id ON "Nova".t0012(payment_term_id);

-- 3. Seed Standard Payment Terms (COD, Net 15, Net 30, Net 60, 2/10 Net 30, Due on Receipt)
INSERT INTO "Nova".t0096 (name, code, description, due_days, discount_percentage, discount_days, is_active, is_default)
VALUES
    ('Net 30', 'NET_30', 'Payment due within 30 days', 30, 0.00, 0, true, true),
    ('Cash on Delivery (COD)', 'COD', 'Payment due immediately upon delivery', 0, 0.00, 0, true, false),
    ('Net 15', 'NET_15', 'Payment due within 15 days', 15, 0.00, 0, true, false),
    ('Net 60', 'NET_60', 'Payment due within 60 days', 60, 0.00, 0, true, false),
    ('2/10 Net 30', '2_10_NET_30', '2% discount if paid within 10 days, net due in 30 days', 30, 2.00, 10, true, false),
    ('Due on Receipt', 'DUE_ON_RECEIPT', 'Payment due immediately upon receipt', 0, 0.00, 0, true, false)
ON CONFLICT (code) DO NOTHING;

COMMIT;

