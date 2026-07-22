-- 015: Per-user UI preferences table
-- Stores layout/theming preferences per user (theme, accent, font, sidebar mode)

CREATE TABLE IF NOT EXISTS "Nova".t0106 (
    id          SERIAL PRIMARY KEY,
    user_id     INT NOT NULL REFERENCES "Nova".t0021(id),
    pref_key    VARCHAR(100) NOT NULL,
    pref_value  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, pref_key)
);

INSERT INTO "Nova".t0106 (user_id, pref_key, pref_value)
SELECT u.id, 'THEME', 'light'
FROM "Nova".t0021 u
ON CONFLICT (user_id, pref_key) DO NOTHING;

INSERT INTO "Nova".t0106 (user_id, pref_key, pref_value)
SELECT u.id, 'ACCENT_COLOR', 'purple'
FROM "Nova".t0021 u
ON CONFLICT (user_id, pref_key) DO NOTHING;

INSERT INTO "Nova".t0106 (user_id, pref_key, pref_value)
SELECT u.id, 'FONT_FAMILY', 'inter'
FROM "Nova".t0021 u
ON CONFLICT (user_id, pref_key) DO NOTHING;

INSERT INTO "Nova".t0106 (user_id, pref_key, pref_value)
SELECT u.id, 'SIDEBAR_MODE', 'expanded'
FROM "Nova".t0021 u
ON CONFLICT (user_id, pref_key) DO NOTHING;
