-- ============================================================
-- Migration 019: Multi-Tenant Isolation (business_id FKs & Composite Indexes)
-- Adds business_id foreign key referencing "Nova".t0059(id)
-- and composite index (business_id, id) across all business tables.
-- ============================================================

BEGIN;

-- T0001
ALTER TABLE "Nova".t0001 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0001_business_id ON "Nova".t0001(business_id);
CREATE INDEX IF NOT EXISTS idx_t0001_business_id_id ON "Nova".t0001(business_id, id);
COMMENT ON COLUMN "Nova".t0001.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0002
ALTER TABLE "Nova".t0002 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0002_business_id ON "Nova".t0002(business_id);
CREATE INDEX IF NOT EXISTS idx_t0002_business_id_id ON "Nova".t0002(business_id, id);
COMMENT ON COLUMN "Nova".t0002.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0003
ALTER TABLE "Nova".t0003 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0003_business_id ON "Nova".t0003(business_id);
CREATE INDEX IF NOT EXISTS idx_t0003_business_id_id ON "Nova".t0003(business_id, id);
COMMENT ON COLUMN "Nova".t0003.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0004
ALTER TABLE "Nova".t0004 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0004_business_id ON "Nova".t0004(business_id);
CREATE INDEX IF NOT EXISTS idx_t0004_business_id_id ON "Nova".t0004(business_id, id);
COMMENT ON COLUMN "Nova".t0004.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0005
ALTER TABLE "Nova".t0005 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0005_business_id ON "Nova".t0005(business_id);
CREATE INDEX IF NOT EXISTS idx_t0005_business_id_id ON "Nova".t0005(business_id, id);
COMMENT ON COLUMN "Nova".t0005.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0006
ALTER TABLE "Nova".t0006 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0006_business_id ON "Nova".t0006(business_id);
CREATE INDEX IF NOT EXISTS idx_t0006_business_id_id ON "Nova".t0006(business_id, id);
COMMENT ON COLUMN "Nova".t0006.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0007
ALTER TABLE "Nova".t0007 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0007_business_id ON "Nova".t0007(business_id);
CREATE INDEX IF NOT EXISTS idx_t0007_business_id_id ON "Nova".t0007(business_id, id);
COMMENT ON COLUMN "Nova".t0007.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0008
ALTER TABLE "Nova".t0008 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0008_business_id ON "Nova".t0008(business_id);
CREATE INDEX IF NOT EXISTS idx_t0008_business_id_id ON "Nova".t0008(business_id, id);
COMMENT ON COLUMN "Nova".t0008.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0009
ALTER TABLE "Nova".t0009 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0009_business_id ON "Nova".t0009(business_id);
CREATE INDEX IF NOT EXISTS idx_t0009_business_id_id ON "Nova".t0009(business_id, id);
COMMENT ON COLUMN "Nova".t0009.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0010
ALTER TABLE "Nova".t0010 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0010_business_id ON "Nova".t0010(business_id);
CREATE INDEX IF NOT EXISTS idx_t0010_business_id_id ON "Nova".t0010(business_id, id);
COMMENT ON COLUMN "Nova".t0010.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0011
ALTER TABLE "Nova".t0011 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0011_business_id ON "Nova".t0011(business_id);
CREATE INDEX IF NOT EXISTS idx_t0011_business_id_id ON "Nova".t0011(business_id, id);
COMMENT ON COLUMN "Nova".t0011.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0012
ALTER TABLE "Nova".t0012 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0012_business_id ON "Nova".t0012(business_id);
CREATE INDEX IF NOT EXISTS idx_t0012_business_id_id ON "Nova".t0012(business_id, id);
COMMENT ON COLUMN "Nova".t0012.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0013
ALTER TABLE "Nova".t0013 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0013_business_id ON "Nova".t0013(business_id);
CREATE INDEX IF NOT EXISTS idx_t0013_business_id_id ON "Nova".t0013(business_id, id);
COMMENT ON COLUMN "Nova".t0013.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0014
ALTER TABLE "Nova".t0014 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0014_business_id ON "Nova".t0014(business_id);
CREATE INDEX IF NOT EXISTS idx_t0014_business_id_id ON "Nova".t0014(business_id, id);
COMMENT ON COLUMN "Nova".t0014.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0015
ALTER TABLE "Nova".t0015 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0015_business_id ON "Nova".t0015(business_id);
CREATE INDEX IF NOT EXISTS idx_t0015_business_id_id ON "Nova".t0015(business_id, id);
COMMENT ON COLUMN "Nova".t0015.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0016
ALTER TABLE "Nova".t0016 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0016_business_id ON "Nova".t0016(business_id);
CREATE INDEX IF NOT EXISTS idx_t0016_business_id_id ON "Nova".t0016(business_id, id);
COMMENT ON COLUMN "Nova".t0016.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0017
ALTER TABLE "Nova".t0017 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0017_business_id ON "Nova".t0017(business_id);
CREATE INDEX IF NOT EXISTS idx_t0017_business_id_id ON "Nova".t0017(business_id, id);
COMMENT ON COLUMN "Nova".t0017.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0018
ALTER TABLE "Nova".t0018 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0018_business_id ON "Nova".t0018(business_id);
CREATE INDEX IF NOT EXISTS idx_t0018_business_id_id ON "Nova".t0018(business_id, id);
COMMENT ON COLUMN "Nova".t0018.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0019
ALTER TABLE "Nova".t0019 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0019_business_id ON "Nova".t0019(business_id);
CREATE INDEX IF NOT EXISTS idx_t0019_business_id_id ON "Nova".t0019(business_id, id);
COMMENT ON COLUMN "Nova".t0019.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0020
ALTER TABLE "Nova".t0020 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0020_business_id ON "Nova".t0020(business_id);
CREATE INDEX IF NOT EXISTS idx_t0020_business_id_id ON "Nova".t0020(business_id, id);
COMMENT ON COLUMN "Nova".t0020.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0021
ALTER TABLE "Nova".t0021 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0021_business_id ON "Nova".t0021(business_id);
CREATE INDEX IF NOT EXISTS idx_t0021_business_id_id ON "Nova".t0021(business_id, id);
COMMENT ON COLUMN "Nova".t0021.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0022
ALTER TABLE "Nova".t0022 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0022_business_id ON "Nova".t0022(business_id);
CREATE INDEX IF NOT EXISTS idx_t0022_business_id_id ON "Nova".t0022(business_id, id);
COMMENT ON COLUMN "Nova".t0022.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0023
ALTER TABLE "Nova".t0023 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0023_business_id ON "Nova".t0023(business_id);
CREATE INDEX IF NOT EXISTS idx_t0023_business_id_id ON "Nova".t0023(business_id, id);
COMMENT ON COLUMN "Nova".t0023.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0024
ALTER TABLE "Nova".t0024 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0024_business_id ON "Nova".t0024(business_id);
CREATE INDEX IF NOT EXISTS idx_t0024_business_id_id ON "Nova".t0024(business_id, id);
COMMENT ON COLUMN "Nova".t0024.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0025
ALTER TABLE "Nova".t0025 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0025_business_id ON "Nova".t0025(business_id);
CREATE INDEX IF NOT EXISTS idx_t0025_business_id_id ON "Nova".t0025(business_id, id);
COMMENT ON COLUMN "Nova".t0025.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0026
ALTER TABLE "Nova".t0026 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0026_business_id ON "Nova".t0026(business_id);
CREATE INDEX IF NOT EXISTS idx_t0026_business_id_id ON "Nova".t0026(business_id, id);
COMMENT ON COLUMN "Nova".t0026.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0027
ALTER TABLE "Nova".t0027 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0027_business_id ON "Nova".t0027(business_id);
CREATE INDEX IF NOT EXISTS idx_t0027_business_id_id ON "Nova".t0027(business_id, id);
COMMENT ON COLUMN "Nova".t0027.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0028
ALTER TABLE "Nova".t0028 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0028_business_id ON "Nova".t0028(business_id);
CREATE INDEX IF NOT EXISTS idx_t0028_business_id_id ON "Nova".t0028(business_id, id);
COMMENT ON COLUMN "Nova".t0028.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0029
ALTER TABLE "Nova".t0029 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0029_business_id ON "Nova".t0029(business_id);
CREATE INDEX IF NOT EXISTS idx_t0029_business_id_id ON "Nova".t0029(business_id, id);
COMMENT ON COLUMN "Nova".t0029.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0030
ALTER TABLE "Nova".t0030 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0030_business_id ON "Nova".t0030(business_id);
CREATE INDEX IF NOT EXISTS idx_t0030_business_id_id ON "Nova".t0030(business_id, id);
COMMENT ON COLUMN "Nova".t0030.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0031
ALTER TABLE "Nova".t0031 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0031_business_id ON "Nova".t0031(business_id);
CREATE INDEX IF NOT EXISTS idx_t0031_business_id_id ON "Nova".t0031(business_id, id);
COMMENT ON COLUMN "Nova".t0031.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0032
ALTER TABLE "Nova".t0032 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0032_business_id ON "Nova".t0032(business_id);
CREATE INDEX IF NOT EXISTS idx_t0032_business_id_id ON "Nova".t0032(business_id, id);
COMMENT ON COLUMN "Nova".t0032.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0033
ALTER TABLE "Nova".t0033 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0033_business_id ON "Nova".t0033(business_id);
CREATE INDEX IF NOT EXISTS idx_t0033_business_id_id ON "Nova".t0033(business_id, id);
COMMENT ON COLUMN "Nova".t0033.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0034
ALTER TABLE "Nova".t0034 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0034_business_id ON "Nova".t0034(business_id);
CREATE INDEX IF NOT EXISTS idx_t0034_business_id_id ON "Nova".t0034(business_id, id);
COMMENT ON COLUMN "Nova".t0034.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0035
ALTER TABLE "Nova".t0035 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0035_business_id ON "Nova".t0035(business_id);
CREATE INDEX IF NOT EXISTS idx_t0035_business_id_id ON "Nova".t0035(business_id, id);
COMMENT ON COLUMN "Nova".t0035.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0036
ALTER TABLE "Nova".t0036 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0036_business_id ON "Nova".t0036(business_id);
CREATE INDEX IF NOT EXISTS idx_t0036_business_id_id ON "Nova".t0036(business_id, id);
COMMENT ON COLUMN "Nova".t0036.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0037
ALTER TABLE "Nova".t0037 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0037_business_id ON "Nova".t0037(business_id);
CREATE INDEX IF NOT EXISTS idx_t0037_business_id_id ON "Nova".t0037(business_id, id);
COMMENT ON COLUMN "Nova".t0037.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0038
ALTER TABLE "Nova".t0038 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0038_business_id ON "Nova".t0038(business_id);
CREATE INDEX IF NOT EXISTS idx_t0038_business_id_id ON "Nova".t0038(business_id, id);
COMMENT ON COLUMN "Nova".t0038.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0039
ALTER TABLE "Nova".t0039 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0039_business_id ON "Nova".t0039(business_id);
CREATE INDEX IF NOT EXISTS idx_t0039_business_id_id ON "Nova".t0039(business_id, id);
COMMENT ON COLUMN "Nova".t0039.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0040
ALTER TABLE "Nova".t0040 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0040_business_id ON "Nova".t0040(business_id);
CREATE INDEX IF NOT EXISTS idx_t0040_business_id_id ON "Nova".t0040(business_id, id);
COMMENT ON COLUMN "Nova".t0040.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0041
ALTER TABLE "Nova".t0041 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0041_business_id ON "Nova".t0041(business_id);
CREATE INDEX IF NOT EXISTS idx_t0041_business_id_id ON "Nova".t0041(business_id, id);
COMMENT ON COLUMN "Nova".t0041.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0042
ALTER TABLE "Nova".t0042 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0042_business_id ON "Nova".t0042(business_id);
CREATE INDEX IF NOT EXISTS idx_t0042_business_id_id ON "Nova".t0042(business_id, id);
COMMENT ON COLUMN "Nova".t0042.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0043
ALTER TABLE "Nova".t0043 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0043_business_id ON "Nova".t0043(business_id);
CREATE INDEX IF NOT EXISTS idx_t0043_business_id_id ON "Nova".t0043(business_id, id);
COMMENT ON COLUMN "Nova".t0043.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0044
ALTER TABLE "Nova".t0044 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0044_business_id ON "Nova".t0044(business_id);
CREATE INDEX IF NOT EXISTS idx_t0044_business_id_id ON "Nova".t0044(business_id, id);
COMMENT ON COLUMN "Nova".t0044.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0045
ALTER TABLE "Nova".t0045 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0045_business_id ON "Nova".t0045(business_id);
CREATE INDEX IF NOT EXISTS idx_t0045_business_id_id ON "Nova".t0045(business_id, id);
COMMENT ON COLUMN "Nova".t0045.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0046
ALTER TABLE "Nova".t0046 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0046_business_id ON "Nova".t0046(business_id);
CREATE INDEX IF NOT EXISTS idx_t0046_business_id_id ON "Nova".t0046(business_id, id);
COMMENT ON COLUMN "Nova".t0046.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0047
ALTER TABLE "Nova".t0047 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0047_business_id ON "Nova".t0047(business_id);
CREATE INDEX IF NOT EXISTS idx_t0047_business_id_id ON "Nova".t0047(business_id, id);
COMMENT ON COLUMN "Nova".t0047.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0048
ALTER TABLE "Nova".t0048 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0048_business_id ON "Nova".t0048(business_id);
CREATE INDEX IF NOT EXISTS idx_t0048_business_id_id ON "Nova".t0048(business_id, id);
COMMENT ON COLUMN "Nova".t0048.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0049
ALTER TABLE "Nova".t0049 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0049_business_id ON "Nova".t0049(business_id);
CREATE INDEX IF NOT EXISTS idx_t0049_business_id_id ON "Nova".t0049(business_id, id);
COMMENT ON COLUMN "Nova".t0049.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0050
ALTER TABLE "Nova".t0050 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0050_business_id ON "Nova".t0050(business_id);
CREATE INDEX IF NOT EXISTS idx_t0050_business_id_id ON "Nova".t0050(business_id, id);
COMMENT ON COLUMN "Nova".t0050.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0051
ALTER TABLE "Nova".t0051 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0051_business_id ON "Nova".t0051(business_id);
CREATE INDEX IF NOT EXISTS idx_t0051_business_id_id ON "Nova".t0051(business_id, id);
COMMENT ON COLUMN "Nova".t0051.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0052
ALTER TABLE "Nova".t0052 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0052_business_id ON "Nova".t0052(business_id);
CREATE INDEX IF NOT EXISTS idx_t0052_business_id_id ON "Nova".t0052(business_id, id);
COMMENT ON COLUMN "Nova".t0052.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0053
ALTER TABLE "Nova".t0053 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0053_business_id ON "Nova".t0053(business_id);
CREATE INDEX IF NOT EXISTS idx_t0053_business_id_id ON "Nova".t0053(business_id, id);
COMMENT ON COLUMN "Nova".t0053.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0054
ALTER TABLE "Nova".t0054 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0054_business_id ON "Nova".t0054(business_id);
CREATE INDEX IF NOT EXISTS idx_t0054_business_id_id ON "Nova".t0054(business_id, id);
COMMENT ON COLUMN "Nova".t0054.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0055
ALTER TABLE "Nova".t0055 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0055_business_id ON "Nova".t0055(business_id);
CREATE INDEX IF NOT EXISTS idx_t0055_business_id_id ON "Nova".t0055(business_id, id);
COMMENT ON COLUMN "Nova".t0055.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0056
ALTER TABLE "Nova".t0056 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0056_business_id ON "Nova".t0056(business_id);
CREATE INDEX IF NOT EXISTS idx_t0056_business_id_id ON "Nova".t0056(business_id, id);
COMMENT ON COLUMN "Nova".t0056.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0057
ALTER TABLE "Nova".t0057 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0057_business_id ON "Nova".t0057(business_id);
CREATE INDEX IF NOT EXISTS idx_t0057_business_id_id ON "Nova".t0057(business_id, id);
COMMENT ON COLUMN "Nova".t0057.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0058
ALTER TABLE "Nova".t0058 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0058_business_id ON "Nova".t0058(business_id);
CREATE INDEX IF NOT EXISTS idx_t0058_business_id_id ON "Nova".t0058(business_id, id);
COMMENT ON COLUMN "Nova".t0058.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0060
ALTER TABLE "Nova".t0060 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0060_business_id ON "Nova".t0060(business_id);
CREATE INDEX IF NOT EXISTS idx_t0060_business_id_id ON "Nova".t0060(business_id, id);
COMMENT ON COLUMN "Nova".t0060.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0061
ALTER TABLE "Nova".t0061 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0061_business_id ON "Nova".t0061(business_id);
CREATE INDEX IF NOT EXISTS idx_t0061_business_id_id ON "Nova".t0061(business_id, id);
COMMENT ON COLUMN "Nova".t0061.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0062
ALTER TABLE "Nova".t0062 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0062_business_id ON "Nova".t0062(business_id);
CREATE INDEX IF NOT EXISTS idx_t0062_business_id_id ON "Nova".t0062(business_id, id);
COMMENT ON COLUMN "Nova".t0062.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0063
ALTER TABLE "Nova".t0063 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0063_business_id ON "Nova".t0063(business_id);
CREATE INDEX IF NOT EXISTS idx_t0063_business_id_id ON "Nova".t0063(business_id, id);
COMMENT ON COLUMN "Nova".t0063.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0064
ALTER TABLE "Nova".t0064 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0064_business_id ON "Nova".t0064(business_id);
CREATE INDEX IF NOT EXISTS idx_t0064_business_id_id ON "Nova".t0064(business_id, id);
COMMENT ON COLUMN "Nova".t0064.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0065
ALTER TABLE "Nova".t0065 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0065_business_id ON "Nova".t0065(business_id);
CREATE INDEX IF NOT EXISTS idx_t0065_business_id_id ON "Nova".t0065(business_id, id);
COMMENT ON COLUMN "Nova".t0065.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0066
ALTER TABLE "Nova".t0066 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0066_business_id ON "Nova".t0066(business_id);
CREATE INDEX IF NOT EXISTS idx_t0066_business_id_id ON "Nova".t0066(business_id, id);
COMMENT ON COLUMN "Nova".t0066.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0067
ALTER TABLE "Nova".t0067 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0067_business_id ON "Nova".t0067(business_id);
CREATE INDEX IF NOT EXISTS idx_t0067_business_id_id ON "Nova".t0067(business_id, id);
COMMENT ON COLUMN "Nova".t0067.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0068
ALTER TABLE "Nova".t0068 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0068_business_id ON "Nova".t0068(business_id);
CREATE INDEX IF NOT EXISTS idx_t0068_business_id_id ON "Nova".t0068(business_id, id);
COMMENT ON COLUMN "Nova".t0068.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0069
ALTER TABLE "Nova".t0069 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0069_business_id ON "Nova".t0069(business_id);
CREATE INDEX IF NOT EXISTS idx_t0069_business_id_id ON "Nova".t0069(business_id, id);
COMMENT ON COLUMN "Nova".t0069.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0070
ALTER TABLE "Nova".t0070 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0070_business_id ON "Nova".t0070(business_id);
CREATE INDEX IF NOT EXISTS idx_t0070_business_id_id ON "Nova".t0070(business_id, id);
COMMENT ON COLUMN "Nova".t0070.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0071
ALTER TABLE "Nova".t0071 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0071_business_id ON "Nova".t0071(business_id);
CREATE INDEX IF NOT EXISTS idx_t0071_business_id_id ON "Nova".t0071(business_id, id);
COMMENT ON COLUMN "Nova".t0071.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0072
ALTER TABLE "Nova".t0072 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0072_business_id ON "Nova".t0072(business_id);
CREATE INDEX IF NOT EXISTS idx_t0072_business_id_id ON "Nova".t0072(business_id, id);
COMMENT ON COLUMN "Nova".t0072.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0073
ALTER TABLE "Nova".t0073 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0073_business_id ON "Nova".t0073(business_id);
CREATE INDEX IF NOT EXISTS idx_t0073_business_id_id ON "Nova".t0073(business_id, id);
COMMENT ON COLUMN "Nova".t0073.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0074
ALTER TABLE "Nova".t0074 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0074_business_id ON "Nova".t0074(business_id);
CREATE INDEX IF NOT EXISTS idx_t0074_business_id_id ON "Nova".t0074(business_id, id);
COMMENT ON COLUMN "Nova".t0074.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0075
ALTER TABLE "Nova".t0075 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0075_business_id ON "Nova".t0075(business_id);
CREATE INDEX IF NOT EXISTS idx_t0075_business_id_id ON "Nova".t0075(business_id, id);
COMMENT ON COLUMN "Nova".t0075.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0076
ALTER TABLE "Nova".t0076 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0076_business_id ON "Nova".t0076(business_id);
CREATE INDEX IF NOT EXISTS idx_t0076_business_id_id ON "Nova".t0076(business_id, id);
COMMENT ON COLUMN "Nova".t0076.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0077
ALTER TABLE "Nova".t0077 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0077_business_id ON "Nova".t0077(business_id);
CREATE INDEX IF NOT EXISTS idx_t0077_business_id_id ON "Nova".t0077(business_id, id);
COMMENT ON COLUMN "Nova".t0077.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0078
ALTER TABLE "Nova".t0078 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0078_business_id ON "Nova".t0078(business_id);
CREATE INDEX IF NOT EXISTS idx_t0078_business_id_id ON "Nova".t0078(business_id, id);
COMMENT ON COLUMN "Nova".t0078.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0079
ALTER TABLE "Nova".t0079 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0079_business_id ON "Nova".t0079(business_id);
CREATE INDEX IF NOT EXISTS idx_t0079_business_id_id ON "Nova".t0079(business_id, id);
COMMENT ON COLUMN "Nova".t0079.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0080
ALTER TABLE "Nova".t0080 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0080_business_id ON "Nova".t0080(business_id);
CREATE INDEX IF NOT EXISTS idx_t0080_business_id_id ON "Nova".t0080(business_id, id);
COMMENT ON COLUMN "Nova".t0080.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0081
ALTER TABLE "Nova".t0081 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0081_business_id ON "Nova".t0081(business_id);
CREATE INDEX IF NOT EXISTS idx_t0081_business_id_id ON "Nova".t0081(business_id, id);
COMMENT ON COLUMN "Nova".t0081.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0082
ALTER TABLE "Nova".t0082 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0082_business_id ON "Nova".t0082(business_id);
CREATE INDEX IF NOT EXISTS idx_t0082_business_id_id ON "Nova".t0082(business_id, id);
COMMENT ON COLUMN "Nova".t0082.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0084
ALTER TABLE "Nova".t0084 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0084_business_id ON "Nova".t0084(business_id);
CREATE INDEX IF NOT EXISTS idx_t0084_business_id_id ON "Nova".t0084(business_id, id);
COMMENT ON COLUMN "Nova".t0084.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0086
ALTER TABLE "Nova".t0086 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0086_business_id ON "Nova".t0086(business_id);
CREATE INDEX IF NOT EXISTS idx_t0086_business_id_id ON "Nova".t0086(business_id, id);
COMMENT ON COLUMN "Nova".t0086.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0087
ALTER TABLE "Nova".t0087 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0087_business_id ON "Nova".t0087(business_id);
CREATE INDEX IF NOT EXISTS idx_t0087_business_id_id ON "Nova".t0087(business_id, id);
COMMENT ON COLUMN "Nova".t0087.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0088
ALTER TABLE "Nova".t0088 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0088_business_id ON "Nova".t0088(business_id);
CREATE INDEX IF NOT EXISTS idx_t0088_business_id_id ON "Nova".t0088(business_id, id);
COMMENT ON COLUMN "Nova".t0088.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0089
ALTER TABLE "Nova".t0089 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0089_business_id ON "Nova".t0089(business_id);
CREATE INDEX IF NOT EXISTS idx_t0089_business_id_id ON "Nova".t0089(business_id, id);
COMMENT ON COLUMN "Nova".t0089.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0090
ALTER TABLE "Nova".t0090 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0090_business_id ON "Nova".t0090(business_id);
CREATE INDEX IF NOT EXISTS idx_t0090_business_id_id ON "Nova".t0090(business_id, id);
COMMENT ON COLUMN "Nova".t0090.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0091
ALTER TABLE "Nova".t0091 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0091_business_id ON "Nova".t0091(business_id);
CREATE INDEX IF NOT EXISTS idx_t0091_business_id_id ON "Nova".t0091(business_id, id);
COMMENT ON COLUMN "Nova".t0091.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0092
ALTER TABLE "Nova".t0092 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0092_business_id ON "Nova".t0092(business_id);
CREATE INDEX IF NOT EXISTS idx_t0092_business_id_id ON "Nova".t0092(business_id, id);
COMMENT ON COLUMN "Nova".t0092.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0093
ALTER TABLE "Nova".t0093 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0093_business_id ON "Nova".t0093(business_id);
CREATE INDEX IF NOT EXISTS idx_t0093_business_id_id ON "Nova".t0093(business_id, id);
COMMENT ON COLUMN "Nova".t0093.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0094
ALTER TABLE "Nova".t0094 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0094_business_id ON "Nova".t0094(business_id);
CREATE INDEX IF NOT EXISTS idx_t0094_business_id_id ON "Nova".t0094(business_id, id);
COMMENT ON COLUMN "Nova".t0094.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0095
ALTER TABLE "Nova".t0095 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0095_business_id ON "Nova".t0095(business_id);
CREATE INDEX IF NOT EXISTS idx_t0095_business_id_id ON "Nova".t0095(business_id, id);
COMMENT ON COLUMN "Nova".t0095.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0096
ALTER TABLE "Nova".t0096 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0096_business_id ON "Nova".t0096(business_id);
CREATE INDEX IF NOT EXISTS idx_t0096_business_id_id ON "Nova".t0096(business_id, id);
COMMENT ON COLUMN "Nova".t0096.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0097
ALTER TABLE "Nova".t0097 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0097_business_id ON "Nova".t0097(business_id);
CREATE INDEX IF NOT EXISTS idx_t0097_business_id_id ON "Nova".t0097(business_id, id);
COMMENT ON COLUMN "Nova".t0097.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0098
ALTER TABLE "Nova".t0098 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0098_business_id ON "Nova".t0098(business_id);
CREATE INDEX IF NOT EXISTS idx_t0098_business_id_id ON "Nova".t0098(business_id, id);
COMMENT ON COLUMN "Nova".t0098.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0099
ALTER TABLE "Nova".t0099 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0099_business_id ON "Nova".t0099(business_id);
CREATE INDEX IF NOT EXISTS idx_t0099_business_id_id ON "Nova".t0099(business_id, id);
COMMENT ON COLUMN "Nova".t0099.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0100
ALTER TABLE "Nova".t0100 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0100_business_id ON "Nova".t0100(business_id);
CREATE INDEX IF NOT EXISTS idx_t0100_business_id_id ON "Nova".t0100(business_id, id);
COMMENT ON COLUMN "Nova".t0100.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0101
ALTER TABLE "Nova".t0101 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0101_business_id ON "Nova".t0101(business_id);
CREATE INDEX IF NOT EXISTS idx_t0101_business_id_id ON "Nova".t0101(business_id, id);
COMMENT ON COLUMN "Nova".t0101.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0102
ALTER TABLE "Nova".t0102 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0102_business_id ON "Nova".t0102(business_id);
CREATE INDEX IF NOT EXISTS idx_t0102_business_id_id ON "Nova".t0102(business_id, id);
COMMENT ON COLUMN "Nova".t0102.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0103
ALTER TABLE "Nova".t0103 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0103_business_id ON "Nova".t0103(business_id);
CREATE INDEX IF NOT EXISTS idx_t0103_business_id_id ON "Nova".t0103(business_id, id);
COMMENT ON COLUMN "Nova".t0103.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0104
ALTER TABLE "Nova".t0104 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0104_business_id ON "Nova".t0104(business_id);
CREATE INDEX IF NOT EXISTS idx_t0104_business_id_id ON "Nova".t0104(business_id, id);
COMMENT ON COLUMN "Nova".t0104.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0105
ALTER TABLE "Nova".t0105 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0105_business_id ON "Nova".t0105(business_id);
CREATE INDEX IF NOT EXISTS idx_t0105_business_id_id ON "Nova".t0105(business_id, id);
COMMENT ON COLUMN "Nova".t0105.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0106
ALTER TABLE "Nova".t0106 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0106_business_id ON "Nova".t0106(business_id);
CREATE INDEX IF NOT EXISTS idx_t0106_business_id_id ON "Nova".t0106(business_id, id);
COMMENT ON COLUMN "Nova".t0106.business_id IS 'Tenant / business organization identifier (FK to T0059)';

-- T0107
ALTER TABLE "Nova".t0107 ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);
CREATE INDEX IF NOT EXISTS idx_t0107_business_id ON "Nova".t0107(business_id);
CREATE INDEX IF NOT EXISTS idx_t0107_business_id_id ON "Nova".t0107(business_id, id);
COMMENT ON COLUMN "Nova".t0107.business_id IS 'Tenant / business organization identifier (FK to T0059)';

COMMIT;
