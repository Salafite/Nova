"""Tests for database migration 027 (Government e-Invoicing & Fiscal Authority Integration)."""
from pathlib import Path
import re


def test_migration_027_file_exists():
    root = Path(__file__).resolve().parents[3]
    mig_path = root / "database" / "migrations" / "027_government_einvoicing_fiscal_authority.sql"
    assert mig_path.exists(), f"Migration file missing at {mig_path}"

    content = mig_path.read_text(encoding="utf-8")
    
    # Check tables t0129 and t0130
    assert 'CREATE TABLE IF NOT EXISTS "Nova".t0129' in content
    assert 'CREATE TABLE IF NOT EXISTS "Nova".t0130' in content
    
    # Check sequences
    assert 'CREATE SEQUENCE IF NOT EXISTS "Nova".seq_einvoice_icv' in content
    assert 'CREATE SEQUENCE IF NOT EXISTS "Nova".seq_fiscal_profile' in content

    # Check multi-tenant business_id FKs to t0059
    assert 'business_id                     INT REFERENCES "Nova".t0059(id)' in content
    assert 'idx_t0129_business_id' in content
    assert 'idx_t0129_business_id_id' in content
    assert 'idx_t0130_business_id' in content
    assert 'idx_t0130_business_id_id' in content

    # Check nova_readonly grant permissions
    assert 'GRANT SELECT ON "Nova".t0129 TO nova_readonly;' in content
    assert 'GRANT SELECT ON "Nova".t0130 TO nova_readonly;' in content
