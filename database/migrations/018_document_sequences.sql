-- Nova ERP — Concurrency-Safe Document Numbering Sequences
-- Migration 018: Add dedicated PostgreSQL sequences for invoices (T0090) and pick lists (T0101)
-- NOTE: Sequences live in the "Nova" schema. packages/database/sequence.py qualifies names with
-- DB_SCHEMA (default 'Nova'), so keep the DDL here consistent with that helper.
BEGIN;

-- 1. Create dedicated sequences in the "Nova" schema
CREATE SEQUENCE IF NOT EXISTS "Nova".seq_invoice_number START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE IF NOT EXISTS "Nova".seq_pick_list_number START WITH 1 INCREMENT BY 1;

-- 2. Synchronize seq_invoice_number with existing maximum invoice number in T0090 (if table exists and has rows)
DO $$
DECLARE
    max_inv_num BIGINT := 0;
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'Nova' AND table_name = 't0090'
    ) THEN
        SELECT COALESCE(MAX(
            CASE
                WHEN invoice_number ~ '^.*-(\d+)$' THEN
                    CASE WHEN LENGTH((regexp_match(invoice_number, '^.*-(\d+)$'))[1]) <= 18
                         THEN (regexp_match(invoice_number, '^.*-(\d+)$'))[1]::BIGINT
                         ELSE 0 END
                WHEN invoice_number ~ '^\d+$' THEN
                    CASE WHEN LENGTH(invoice_number) <= 18
                         THEN invoice_number::BIGINT
                         ELSE 0 END
                ELSE 0
            END
        ), 0)
        INTO max_inv_num
        FROM "Nova".t0090;
    END IF;

    IF max_inv_num > 0 THEN
        PERFORM setval('"Nova".seq_invoice_number', max_inv_num, true);
    ELSE
        PERFORM setval('"Nova".seq_invoice_number', 1, false);
    END IF;
END $$;

-- 3. Synchronize seq_pick_list_number with existing maximum pick list number in T0101 (if table exists and has rows)
DO $$
DECLARE
    max_pkl_num BIGINT := 0;
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'Nova' AND table_name = 't0101'
    ) THEN
        SELECT COALESCE(MAX(
            CASE
                WHEN pick_list_number ~ '^.*-(\d+)$' THEN
                    CASE WHEN LENGTH((regexp_match(pick_list_number, '^.*-(\d+)$'))[1]) <= 18
                         THEN (regexp_match(pick_list_number, '^.*-(\d+)$'))[1]::BIGINT
                         ELSE 0 END
                WHEN pick_list_number ~ '^\d+$' THEN
                    CASE WHEN LENGTH(pick_list_number) <= 18
                         THEN pick_list_number::BIGINT
                         ELSE 0 END
                ELSE 0
            END
        ), 0)
        INTO max_pkl_num
        FROM "Nova".t0101;
    END IF;

    IF max_pkl_num > 0 THEN
        PERFORM setval('"Nova".seq_pick_list_number', max_pkl_num, true);
    ELSE
        PERFORM setval('"Nova".seq_pick_list_number', 1, false);
    END IF;
END $$;

COMMENT ON SEQUENCE "Nova".seq_invoice_number IS 'Concurrency-safe atomic sequence for generating unique invoice numbers (INV-XXXXX)';
COMMENT ON SEQUENCE "Nova".seq_pick_list_number IS 'Concurrency-safe atomic sequence for generating unique pick list numbers (PKL-XXXXX)';

COMMIT;
