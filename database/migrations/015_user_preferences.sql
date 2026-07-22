-- 015: Per-user UI preferences table
-- Stores layout/theming preferences per user (theme, accent, font, sidebar mode)

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'Nova' AND tablename = 't0106') THEN
    CREATE TABLE "Nova".t0106 (
        id          SERIAL PRIMARY KEY,
        user_id     INT NOT NULL,
        pref_key    VARCHAR(100) NOT NULL,
        pref_value  TEXT,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(user_id, pref_key)
    );

    ALTER TABLE "Nova".t0106 ADD CONSTRAINT fk_t0106_user_id
        FOREIGN KEY (user_id) REFERENCES "Nova".t0021(id);

    INSERT INTO "Nova".t0106 (user_id, pref_key, pref_value)
    SELECT u.id, 'THEME', 'light' FROM "Nova".t0021 u
    ON CONFLICT (user_id, pref_key) DO NOTHING;

    INSERT INTO "Nova".t0106 (user_id, pref_key, pref_value)
    SELECT u.id, 'ACCENT_COLOR', 'purple' FROM "Nova".t0021 u
    ON CONFLICT (user_id, pref_key) DO NOTHING;

    INSERT INTO "Nova".t0106 (user_id, pref_key, pref_value)
    SELECT u.id, 'FONT_FAMILY', 'inter' FROM "Nova".t0021 u
    ON CONFLICT (user_id, pref_key) DO NOTHING;

    INSERT INTO "Nova".t0106 (user_id, pref_key, pref_value)
    SELECT u.id, 'SIDEBAR_MODE', 'expanded' FROM "Nova".t0021 u
    ON CONFLICT (user_id, pref_key) DO NOTHING;
  END IF;
END $$;
