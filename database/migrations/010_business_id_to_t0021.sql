-- Add business_id column to users table
ALTER TABLE "Nova".t0021 ADD COLUMN IF NOT EXISTS business_id INT;
CREATE INDEX IF NOT EXISTS idx_t0021_business_id ON "Nova".t0021(business_id);
