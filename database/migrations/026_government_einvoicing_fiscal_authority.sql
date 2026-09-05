-- Nova ERP — Government e-Invoicing & Fiscal Authority Integration (ZATCA / Tax QR)
-- Migration 026: E-Invoice Fiscal Clearance & Cryptographic Records (T0124),
--                Fiscal Authority Profiles & Tax Credentials (T0125)
BEGIN;

-- 1. Sequences
CREATE SEQUENCE IF NOT EXISTS "Nova".seq_einvoice_icv START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_einvoice_icv IS 'Atomic sequence for generating sequential Invoice Counter Values (ICV)';

CREATE SEQUENCE IF NOT EXISTS "Nova".seq_fiscal_profile START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_fiscal_profile IS 'Atomic sequence for fiscal authority profile numbering';

-- 2. Fiscal Authority Profiles & Tax Credentials Table (T0125)
CREATE TABLE IF NOT EXISTS "Nova".t0125 (
    id                              SERIAL PRIMARY KEY,
    profile_name                    VARCHAR(100) NOT NULL,
    authority_code                  VARCHAR(50) NOT NULL DEFAULT 'ZATCA',
    seller_name                     VARCHAR(255) NOT NULL,
    seller_name_ar                  VARCHAR(255),
    tax_id                          VARCHAR(50) NOT NULL,
    commercial_registration_number  VARCHAR(50),
    building_number                 VARCHAR(20),
    street_name                     VARCHAR(255),
    street_name_ar                  VARCHAR(255),
    district                        VARCHAR(100),
    district_ar                     VARCHAR(100),
    city                            VARCHAR(100),
    city_ar                         VARCHAR(100),
    postal_code                     VARCHAR(20),
    country_code                    VARCHAR(10) NOT NULL DEFAULT 'SA',
    environment                     VARCHAR(30) NOT NULL DEFAULT 'Sandbox',
    api_base_url                    VARCHAR(255),
    api_key                         VARCHAR(255),
    api_secret                      VARCHAR(255),
    auth_token                      TEXT,
    token_expires_at                TIMESTAMPTZ,
    csid                            TEXT,
    csid_secret                     TEXT,
    private_key                     TEXT,
    public_key                      TEXT,
    certificate                     TEXT,
    is_active                       BOOLEAN NOT NULL DEFAULT true,
    business_id                     INT REFERENCES "Nova".t0059(id),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by                      INT,
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by                      INT,
    update_number                   INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0125 IS 'Fiscal Authority Profiles & Tax Credentials — Configured fiscal authority profiles, cryptographic keys, and API credentials';
COMMENT ON COLUMN "Nova".t0125.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0125.profile_name IS 'Descriptive name for the fiscal profile (e.g. Main Branch ZATCA)';
COMMENT ON COLUMN "Nova".t0125.authority_code IS 'Fiscal tax authority code: ZATCA | PEPPOL | NTS | GENERIC';
COMMENT ON COLUMN "Nova".t0125.seller_name IS 'Official legal registered business name in English/Latin';
COMMENT ON COLUMN "Nova".t0125.seller_name_ar IS 'Official legal registered business name in Arabic';
COMMENT ON COLUMN "Nova".t0125.tax_id IS 'Tax Registration Number / VAT Number';
COMMENT ON COLUMN "Nova".t0125.environment IS 'Target environment: Sandbox | Simulation | Production';
COMMENT ON COLUMN "Nova".t0125.csid IS 'Compliance or Production Cryptographic Stamp Identifier (CSID)';
COMMENT ON COLUMN "Nova".t0125.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0125_authority_code ON "Nova".t0125(authority_code);
CREATE INDEX IF NOT EXISTS idx_t0125_tax_id ON "Nova".t0125(tax_id);
CREATE INDEX IF NOT EXISTS idx_t0125_environment ON "Nova".t0125(environment);
CREATE INDEX IF NOT EXISTS idx_t0125_business_id ON "Nova".t0125(business_id);
CREATE INDEX IF NOT EXISTS idx_t0125_business_id_id ON "Nova".t0125(business_id, id);

-- 3. E-Invoice Fiscal Clearance & Cryptographic Records Table (T0124)
CREATE TABLE IF NOT EXISTS "Nova".t0124 (
    id                  SERIAL PRIMARY KEY,
    invoice_id          INT NOT NULL REFERENCES "Nova".t0090(id) ON DELETE CASCADE,
    fiscal_profile_id   INT REFERENCES "Nova".t0125(id) ON DELETE SET NULL,
    invoice_uuid        VARCHAR(100) NOT NULL,
    invoice_type_code   VARCHAR(50) NOT NULL DEFAULT '388',
    subtype             VARCHAR(50) NOT NULL DEFAULT '0100000',
    icv                 INT NOT NULL DEFAULT 1,
    pih                 VARCHAR(255),
    invoice_hash        VARCHAR(255) NOT NULL,
    digital_signature   TEXT,
    public_key          TEXT,
    certificate         TEXT,
    qr_code_tlv         TEXT,
    ubl_xml             TEXT,
    clearance_status    VARCHAR(30) NOT NULL DEFAULT 'Pending',
    clearance_date      TIMESTAMPTZ,
    clearance_id        VARCHAR(100),
    validation_results  JSONB,
    rejection_reason    TEXT,
    environment         VARCHAR(30) NOT NULL DEFAULT 'Sandbox',
    is_reported         BOOLEAN NOT NULL DEFAULT false,
    is_cleared          BOOLEAN NOT NULL DEFAULT false,
    business_id         INT REFERENCES "Nova".t0059(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0124 IS 'E-Invoice Fiscal Clearance & Cryptographic Records — Fiscal cryptographic seals, UBL XMLs, QR codes, and clearance statuses';
COMMENT ON COLUMN "Nova".t0124.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0124.invoice_id IS 'Associated sales invoice reference (FK to t0090)';
COMMENT ON COLUMN "Nova".t0124.fiscal_profile_id IS 'Fiscal authority profile used for signing & clearance (FK to t0125)';
COMMENT ON COLUMN "Nova".t0124.invoice_uuid IS 'Universally Unique Identifier for the e-invoice (UUID v4)';
COMMENT ON COLUMN "Nova".t0124.invoice_type_code IS 'UN/ECE 1001 invoice type code (388=Tax Invoice, 381=Credit Note, 383=Debit Note)';
COMMENT ON COLUMN "Nova".t0124.subtype IS 'Fiscal transaction subtype (0100000=Standard B2B, 0200000=Simplified B2C, etc.)';
COMMENT ON COLUMN "Nova".t0124.icv IS 'Invoice Counter Value sequential number';
COMMENT ON COLUMN "Nova".t0124.pih IS 'Previous Invoice Hash (Base64 SHA-256) for audit trail chaining';
COMMENT ON COLUMN "Nova".t0124.invoice_hash IS 'Canonical SHA-256 hash of the generated invoice UBL XML';
COMMENT ON COLUMN "Nova".t0124.digital_signature IS 'ECDSA/RSA digital cryptographic signature';
COMMENT ON COLUMN "Nova".t0124.qr_code_tlv IS 'Base64 encoded Tag-Length-Value (TLV) QR code data string';
COMMENT ON COLUMN "Nova".t0124.ubl_xml IS 'Full canonical / signed UBL 2.1 XML document content';
COMMENT ON COLUMN "Nova".t0124.clearance_status IS 'Fiscal clearance state: Pending | Cleared | Reported | Rejected | Failed | Not_Submitted';
COMMENT ON COLUMN "Nova".t0124.clearance_id IS 'Tax authority clearance UUID / Invoice Reference Number (IRN)';
COMMENT ON COLUMN "Nova".t0124.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0124_invoice_id ON "Nova".t0124(invoice_id);
CREATE INDEX IF NOT EXISTS idx_t0124_fiscal_profile_id ON "Nova".t0124(fiscal_profile_id);
CREATE INDEX IF NOT EXISTS idx_t0124_invoice_uuid ON "Nova".t0124(invoice_uuid);
CREATE INDEX IF NOT EXISTS idx_t0124_clearance_status ON "Nova".t0124(clearance_status);
CREATE INDEX IF NOT EXISTS idx_t0124_business_id ON "Nova".t0124(business_id);
CREATE INDEX IF NOT EXISTS idx_t0124_business_id_id ON "Nova".t0124(business_id, id);

-- 4. Grant Readonly Permissions to AI / MCP Role
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        GRANT SELECT ON "Nova".t0124 TO nova_readonly;
        GRANT SELECT ON "Nova".t0125 TO nova_readonly;
    END IF;
END $$;

COMMIT;
