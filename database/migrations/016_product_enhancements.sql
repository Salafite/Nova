-- Nova ERP — Product & Attribute Enhancements (Odoo-like fields)
BEGIN;

ALTER TABLE "Nova".t0003
  ADD COLUMN IF NOT EXISTS description TEXT,
  ADD COLUMN IF NOT EXISTS barcode VARCHAR(100),
  ADD COLUMN IF NOT EXISTS type VARCHAR(20) NOT NULL DEFAULT 'stockable',
  ADD COLUMN IF NOT EXISTS is_purchasable BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS is_saleable BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS weight NUMERIC(10,3) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS volume NUMERIC(10,3) NOT NULL DEFAULT 0;

COMMENT ON COLUMN "Nova".t0003.description IS 'Product description / internal notes';
COMMENT ON COLUMN "Nova".t0003.barcode IS 'Primary barcode / EAN / UPC';
COMMENT ON COLUMN "Nova".t0003.type IS 'Product type: stockable, consumable, service';
COMMENT ON COLUMN "Nova".t0003.is_purchasable IS 'Can be purchased from suppliers';
COMMENT ON COLUMN "Nova".t0003.is_saleable IS 'Can be sold to customers';
COMMENT ON COLUMN "Nova".t0003.weight IS 'Weight in kg';
COMMENT ON COLUMN "Nova".t0003.volume IS 'Volume in m3';

ALTER TABLE "Nova".t0005
  ADD COLUMN IF NOT EXISTS display_type VARCHAR(20) NOT NULL DEFAULT 'select',
  ADD COLUMN IF NOT EXISTS description TEXT,
  ADD COLUMN IF NOT EXISTS create_variant BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS attribute_group VARCHAR(100);

COMMENT ON COLUMN "Nova".t0005.display_type IS 'Display type: select, radio, color, multi';
COMMENT ON COLUMN "Nova".t0005.description IS 'Attribute description / help text';
COMMENT ON COLUMN "Nova".t0005.create_variant IS 'Generate product variants from this attribute';
COMMENT ON COLUMN "Nova".t0005.attribute_group IS 'Attribute group / category';

COMMIT;
