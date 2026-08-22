-- ============================================================
-- Migration 019a: Add missing Price Lists and Tax Rates tables
-- t0083 (Price Lists) and t0085 (Tax Rates) are referenced by
-- t0084 and t0086 but were never created in earlier migrations.
-- ============================================================

BEGIN;

-- T0083 — Price Lists
CREATE TABLE IF NOT EXISTS "Nova".t0083 (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
COMMENT ON TABLE "Nova".t0083 IS 'Price Lists';
COMMENT ON COLUMN "Nova".t0083.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0083.name IS 'Price list name';
COMMENT ON COLUMN "Nova".t0083.code IS 'Unique price list code';
CREATE INDEX IF NOT EXISTS idx_t0083_code ON "Nova".t0083(code);
CREATE INDEX IF NOT EXISTS idx_t0083_active ON "Nova".t0083(is_active);

-- T0085 — Tax Rates
CREATE TABLE IF NOT EXISTS "Nova".t0085 (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    rate NUMERIC(5,2) NOT NULL DEFAULT 0,
    type VARCHAR(50) DEFAULT 'Percentage',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
COMMENT ON TABLE "Nova".t0085 IS 'Tax Rates';
COMMENT ON COLUMN "Nova".t0085.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0085.code IS 'Tax rate code';
COMMENT ON COLUMN "Nova".t0085.type IS 'Tax type';
COMMENT ON COLUMN "Nova".t0085.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0085_code ON "Nova".t0085(code);
CREATE INDEX IF NOT EXISTS idx_t0085_type ON "Nova".t0085(type);
CREATE INDEX IF NOT EXISTS idx_t0085_active ON "Nova".t0085(is_active);

COMMIT;
