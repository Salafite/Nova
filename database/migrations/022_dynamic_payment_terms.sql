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

COMMIT;
