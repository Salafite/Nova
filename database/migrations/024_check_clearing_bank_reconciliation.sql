-- Nova ERP — Electronic Check Clearing & Bank Statement Reconciliation
-- Migration 024: Bank Statements (T0116), Statement Transactions (T0117), Check Clearing Records (T0118)
BEGIN;

-- 1. Sequences for Bank Statements and Check Clearing Records
CREATE SEQUENCE IF NOT EXISTS "Nova".seq_bank_statement_number START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_bank_statement_number IS 'Atomic sequence for generating unique bank statement numbers (STMT-XXXXX)';

CREATE SEQUENCE IF NOT EXISTS "Nova".seq_check_clearing_number START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_check_clearing_number IS 'Atomic sequence for generating unique check clearing transaction numbers (CLR-XXXXX)';

-- 2. Bank Statements Master Table (T0116)
CREATE TABLE IF NOT EXISTS "Nova".t0116 (
    id                      SERIAL PRIMARY KEY,
    statement_number        VARCHAR(50) NOT NULL UNIQUE,
    bank_name               VARCHAR(100) NOT NULL,
    account_number          VARCHAR(50) NOT NULL,
    statement_date          DATE NOT NULL DEFAULT CURRENT_DATE,
    start_date              DATE,
    end_date                DATE,
    opening_balance         NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    closing_balance         NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    total_deposits          NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    total_withdrawals       NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    file_name               VARCHAR(255),
    file_type               VARCHAR(20) NOT NULL DEFAULT 'OFX',
    status                  VARCHAR(30) NOT NULL DEFAULT 'Uploaded',
    total_transactions      INT NOT NULL DEFAULT 0,
    matched_count           INT NOT NULL DEFAULT 0,
    unmatched_count         INT NOT NULL DEFAULT 0,
    notes                   TEXT,
    is_active               BOOLEAN NOT NULL DEFAULT true,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0116 IS 'Bank Statements — Uploaded OFX/CSV bank statement files for reconciliation';
COMMENT ON COLUMN "Nova".t0116.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0116.statement_number IS 'Unique bank statement identification code (STMT-XXXXX)';
COMMENT ON COLUMN "Nova".t0116.bank_name IS 'Name of the issuing bank / financial institution';
COMMENT ON COLUMN "Nova".t0116.account_number IS 'Bank account number associated with the statement';
COMMENT ON COLUMN "Nova".t0116.statement_date IS 'Statement generation or import date';
COMMENT ON COLUMN "Nova".t0116.opening_balance IS 'Opening account balance as reported on statement';
COMMENT ON COLUMN "Nova".t0116.closing_balance IS 'Closing account balance as reported on statement';
COMMENT ON COLUMN "Nova".t0116.file_type IS 'Source file format: OFX | QFX | CSV';
COMMENT ON COLUMN "Nova".t0116.status IS 'Statement processing status: Uploaded | Processing | Matched | Reconciled | Cancelled';
COMMENT ON COLUMN "Nova".t0116.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0116_statement_number ON "Nova".t0116(statement_number);
CREATE INDEX IF NOT EXISTS idx_t0116_statement_date ON "Nova".t0116(statement_date);
CREATE INDEX IF NOT EXISTS idx_t0116_status ON "Nova".t0116(status);
CREATE INDEX IF NOT EXISTS idx_t0116_business_id ON "Nova".t0116(business_id);
CREATE INDEX IF NOT EXISTS idx_t0116_business_id_id ON "Nova".t0116(business_id, id);

-- 3. Statement Transactions Table (T0117)
CREATE TABLE IF NOT EXISTS "Nova".t0117 (
    id                      SERIAL PRIMARY KEY,
    statement_id            INT NOT NULL REFERENCES "Nova".t0116(id) ON DELETE CASCADE,
    transaction_date        DATE NOT NULL,
    fit_id                  VARCHAR(100),
    check_number            VARCHAR(50),
    payee_name              VARCHAR(255),
    memo                    TEXT,
    amount                  NUMERIC(12,2) NOT NULL,
    transaction_type        VARCHAR(50) NOT NULL DEFAULT 'CHECK',
    match_status            VARCHAR(30) NOT NULL DEFAULT 'Pending',
    matched_payment_id      INT REFERENCES "Nova".t0027(id),
    match_score             NUMERIC(5,2),
    notes                   TEXT,
    is_active               BOOLEAN NOT NULL DEFAULT true,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0117 IS 'Statement Transactions — Individual line-item transactions parsed from bank statements';
COMMENT ON COLUMN "Nova".t0117.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0117.statement_id IS 'Parent bank statement reference (FK to t0116)';
COMMENT ON COLUMN "Nova".t0117.transaction_date IS 'Bank posting / clear date';
COMMENT ON COLUMN "Nova".t0117.fit_id IS 'Financial Institution Transaction ID (OFX unique identifier)';
COMMENT ON COLUMN "Nova".t0117.check_number IS 'Extracted check number';
COMMENT ON COLUMN "Nova".t0117.amount IS 'Transaction amount (positive for deposit, negative for withdrawal)';
COMMENT ON COLUMN "Nova".t0117.match_status IS 'Reconciliation match status: Pending | Matched | Cleared | Bounced | Unmatched';
COMMENT ON COLUMN "Nova".t0117.matched_payment_id IS 'Matched Nova ERP payment record (FK to t0027)';
COMMENT ON COLUMN "Nova".t0117.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0117_statement_id ON "Nova".t0117(statement_id);
CREATE INDEX IF NOT EXISTS idx_t0117_check_number ON "Nova".t0117(check_number);
CREATE INDEX IF NOT EXISTS idx_t0117_transaction_date ON "Nova".t0117(transaction_date);
CREATE INDEX IF NOT EXISTS idx_t0117_match_status ON "Nova".t0117(match_status);
CREATE INDEX IF NOT EXISTS idx_t0117_matched_payment_id ON "Nova".t0117(matched_payment_id);
CREATE INDEX IF NOT EXISTS idx_t0117_business_id ON "Nova".t0117(business_id);
CREATE INDEX IF NOT EXISTS idx_t0117_business_id_id ON "Nova".t0117(business_id, id);

-- 4. Check Clearing Records Table (T0118)
CREATE TABLE IF NOT EXISTS "Nova".t0118 (
    id                      SERIAL PRIMARY KEY,
    clearing_number         VARCHAR(50) NOT NULL UNIQUE,
    payment_id              INT REFERENCES "Nova".t0027(id),
    statement_transaction_id INT REFERENCES "Nova".t0117(id) ON DELETE SET NULL,
    customer_id             INT REFERENCES "Nova".t0010(id),
    check_number            VARCHAR(50) NOT NULL,
    bank_name               VARCHAR(100),
    payee_payer             VARCHAR(255),
    amount                  NUMERIC(12,2) NOT NULL,
    issue_date              DATE,
    clearing_date           DATE,
    status                  VARCHAR(30) NOT NULL DEFAULT 'Pending',
    bounced_date            DATE,
    bounced_reason          TEXT,
    penalty_fee             NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    credit_hold_triggered   BOOLEAN NOT NULL DEFAULT false,
    notes                   TEXT,
    is_active               BOOLEAN NOT NULL DEFAULT true,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0118 IS 'Check Clearing Records — Detailed tracking of check status, clearing events, and bounced check workflows';
COMMENT ON COLUMN "Nova".t0118.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0118.clearing_number IS 'Unique check clearing record identifier (CLR-XXXXX)';
COMMENT ON COLUMN "Nova".t0118.payment_id IS 'Associated Nova ERP payment reference (FK to t0027)';
COMMENT ON COLUMN "Nova".t0118.statement_transaction_id IS 'Associated bank statement transaction line (FK to t0117)';
COMMENT ON COLUMN "Nova".t0118.customer_id IS 'Associated customer reference (FK to t0010)';
COMMENT ON COLUMN "Nova".t0118.check_number IS 'Check number';
COMMENT ON COLUMN "Nova".t0118.status IS 'Check status: Pending | Matched | Cleared | Bounced | Unmatched';
COMMENT ON COLUMN "Nova".t0118.penalty_fee IS 'NSF / bounced check penalty fee assessed';
COMMENT ON COLUMN "Nova".t0118.credit_hold_triggered IS 'Flag indicating if customer credit hold was automatically triggered on bounce';
COMMENT ON COLUMN "Nova".t0118.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0118_clearing_number ON "Nova".t0118(clearing_number);
CREATE INDEX IF NOT EXISTS idx_t0118_payment_id ON "Nova".t0118(payment_id);
CREATE INDEX IF NOT EXISTS idx_t0118_statement_transaction_id ON "Nova".t0118(statement_transaction_id);
CREATE INDEX IF NOT EXISTS idx_t0118_customer_id ON "Nova".t0118(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0118_check_number ON "Nova".t0118(check_number);
CREATE INDEX IF NOT EXISTS idx_t0118_status ON "Nova".t0118(status);
CREATE INDEX IF NOT EXISTS idx_t0118_clearing_date ON "Nova".t0118(clearing_date);
CREATE INDEX IF NOT EXISTS idx_t0118_issue_date ON "Nova".t0118(issue_date);
CREATE INDEX IF NOT EXISTS idx_t0118_business_id ON "Nova".t0118(business_id);
CREATE INDEX IF NOT EXISTS idx_t0118_business_id_id ON "Nova".t0118(business_id, id);

-- 5. Grant Readonly Permissions to AI / MCP Role
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        GRANT SELECT ON "Nova".t0116 TO nova_readonly;
        GRANT SELECT ON "Nova".t0117 TO nova_readonly;
        GRANT SELECT ON "Nova".t0118 TO nova_readonly;
    END IF;
END $$;

COMMIT;
