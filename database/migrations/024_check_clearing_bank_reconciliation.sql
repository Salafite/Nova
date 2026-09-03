-- Nova ERP — Electronic Check Clearing & Bank Statement Reconciliation
-- Migration 024: Bank Statements (T0108), Statement Transactions (T0109), Check Clearing Records (T0110)
BEGIN;

-- 1. Sequences for Bank Statements and Check Clearing Records
CREATE SEQUENCE IF NOT EXISTS "Nova".seq_bank_statement_number START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_bank_statement_number IS 'Atomic sequence for generating unique bank statement numbers (STMT-XXXXX)';

CREATE SEQUENCE IF NOT EXISTS "Nova".seq_check_clearing_number START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_check_clearing_number IS 'Atomic sequence for generating unique check clearing transaction numbers (CLR-XXXXX)';

-- 2. Bank Statements Master Table (T0108)
CREATE TABLE IF NOT EXISTS "Nova".t0108 (
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

COMMENT ON TABLE "Nova".t0108 IS 'Bank Statements — Uploaded OFX/CSV bank statement files for reconciliation';
COMMENT ON COLUMN "Nova".t0108.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0108.statement_number IS 'Unique bank statement identification code (STMT-XXXXX)';
COMMENT ON COLUMN "Nova".t0108.bank_name IS 'Name of the issuing bank / financial institution';
COMMENT ON COLUMN "Nova".t0108.account_number IS 'Bank account number associated with the statement';
COMMENT ON COLUMN "Nova".t0108.statement_date IS 'Statement generation or import date';
COMMENT ON COLUMN "Nova".t0108.opening_balance IS 'Opening account balance as reported on statement';
COMMENT ON COLUMN "Nova".t0108.closing_balance IS 'Closing account balance as reported on statement';
COMMENT ON COLUMN "Nova".t0108.file_type IS 'Source file format: OFX | QFX | CSV';
COMMENT ON COLUMN "Nova".t0108.status IS 'Statement processing status: Uploaded | Processing | Matched | Reconciled | Cancelled';
COMMENT ON COLUMN "Nova".t0108.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0108_statement_number ON "Nova".t0108(statement_number);
CREATE INDEX IF NOT EXISTS idx_t0108_statement_date ON "Nova".t0108(statement_date);
CREATE INDEX IF NOT EXISTS idx_t0108_status ON "Nova".t0108(status);
CREATE INDEX IF NOT EXISTS idx_t0108_business_id ON "Nova".t0108(business_id);
CREATE INDEX IF NOT EXISTS idx_t0108_business_id_id ON "Nova".t0108(business_id, id);

-- 3. Statement Transactions Table (T0109)
CREATE TABLE IF NOT EXISTS "Nova".t0109 (
    id                      SERIAL PRIMARY KEY,
    statement_id            INT NOT NULL REFERENCES "Nova".t0108(id) ON DELETE CASCADE,
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

COMMENT ON TABLE "Nova".t0109 IS 'Statement Transactions — Individual line-item transactions parsed from bank statements';
COMMENT ON COLUMN "Nova".t0109.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0109.statement_id IS 'Parent bank statement reference (FK to t0108)';
COMMENT ON COLUMN "Nova".t0109.transaction_date IS 'Bank posting / clear date';
COMMENT ON COLUMN "Nova".t0109.fit_id IS 'Financial Institution Transaction ID (OFX unique identifier)';
COMMENT ON COLUMN "Nova".t0109.check_number IS 'Extracted check number';
COMMENT ON COLUMN "Nova".t0109.amount IS 'Transaction amount (positive for deposit, negative for withdrawal)';
COMMENT ON COLUMN "Nova".t0109.match_status IS 'Reconciliation match status: Pending | Matched | Cleared | Bounced | Unmatched';
COMMENT ON COLUMN "Nova".t0109.matched_payment_id IS 'Matched Nova ERP payment record (FK to t0027)';
COMMENT ON COLUMN "Nova".t0109.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0109_statement_id ON "Nova".t0109(statement_id);
CREATE INDEX IF NOT EXISTS idx_t0109_check_number ON "Nova".t0109(check_number);
CREATE INDEX IF NOT EXISTS idx_t0109_transaction_date ON "Nova".t0109(transaction_date);
CREATE INDEX IF NOT EXISTS idx_t0109_match_status ON "Nova".t0109(match_status);
CREATE INDEX IF NOT EXISTS idx_t0109_matched_payment_id ON "Nova".t0109(matched_payment_id);
CREATE INDEX IF NOT EXISTS idx_t0109_business_id ON "Nova".t0109(business_id);
CREATE INDEX IF NOT EXISTS idx_t0109_business_id_id ON "Nova".t0109(business_id, id);

-- 4. Check Clearing Records Table (T0110)
CREATE TABLE IF NOT EXISTS "Nova".t0110 (
    id                      SERIAL PRIMARY KEY,
    clearing_number         VARCHAR(50) NOT NULL UNIQUE,
    payment_id              INT REFERENCES "Nova".t0027(id),
    statement_transaction_id INT REFERENCES "Nova".t0109(id) ON DELETE SET NULL,
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

COMMENT ON TABLE "Nova".t0110 IS 'Check Clearing Records — Detailed tracking of check status, clearing events, and bounced check workflows';
COMMENT ON COLUMN "Nova".t0110.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0110.clearing_number IS 'Unique check clearing record identifier (CLR-XXXXX)';
COMMENT ON COLUMN "Nova".t0110.payment_id IS 'Associated Nova ERP payment reference (FK to t0027)';
COMMENT ON COLUMN "Nova".t0110.statement_transaction_id IS 'Associated bank statement transaction line (FK to t0109)';
COMMENT ON COLUMN "Nova".t0110.customer_id IS 'Associated customer reference (FK to t0010)';
COMMENT ON COLUMN "Nova".t0110.check_number IS 'Check number';
COMMENT ON COLUMN "Nova".t0110.status IS 'Check status: Pending | Matched | Cleared | Bounced | Unmatched';
COMMENT ON COLUMN "Nova".t0110.penalty_fee IS 'NSF / bounced check penalty fee assessed';
COMMENT ON COLUMN "Nova".t0110.credit_hold_triggered IS 'Flag indicating if customer credit hold was automatically triggered on bounce';
COMMENT ON COLUMN "Nova".t0110.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0110_clearing_number ON "Nova".t0110(clearing_number);
CREATE INDEX IF NOT EXISTS idx_t0110_payment_id ON "Nova".t0110(payment_id);
CREATE INDEX IF NOT EXISTS idx_t0110_statement_transaction_id ON "Nova".t0110(statement_transaction_id);
CREATE INDEX IF NOT EXISTS idx_t0110_customer_id ON "Nova".t0110(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0110_check_number ON "Nova".t0110(check_number);
CREATE INDEX IF NOT EXISTS idx_t0110_status ON "Nova".t0110(status);
CREATE INDEX IF NOT EXISTS idx_t0110_clearing_date ON "Nova".t0110(clearing_date);
CREATE INDEX IF NOT EXISTS idx_t0110_issue_date ON "Nova".t0110(issue_date);
CREATE INDEX IF NOT EXISTS idx_t0110_business_id ON "Nova".t0110(business_id);
CREATE INDEX IF NOT EXISTS idx_t0110_business_id_id ON "Nova".t0110(business_id, id);

-- 5. Grant Readonly Permissions to AI / MCP Role
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        GRANT SELECT ON "Nova".t0108 TO nova_readonly;
        GRANT SELECT ON "Nova".t0109 TO nova_readonly;
        GRANT SELECT ON "Nova".t0110 TO nova_readonly;
    END IF;
END $$;

COMMIT;
