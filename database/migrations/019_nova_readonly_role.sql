-- Nova ERP — Read-Only Role & Column-Level Security Migration for AI Agents
BEGIN;

-- 1. Create nova_readonly role if not exists
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        CREATE ROLE nova_readonly NOLOGIN;
    END IF;
END $$;

-- 2. Grant USAGE on schema "Nova"
GRANT USAGE ON SCHEMA "Nova" TO nova_readonly;

-- 3. Grant SELECT on all existing and default tables in schema "Nova"
GRANT SELECT ON ALL TABLES IN SCHEMA "Nova" TO nova_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA "Nova" GRANT SELECT ON TABLES TO nova_readonly;

-- 4. Column-level restrictions on sensitive credential columns
-- Revoke full table SELECT on t0021 (Users) and grant only non-credential columns
REVOKE SELECT ON "Nova".t0021 FROM nova_readonly;
GRANT SELECT (id, username, full_name, email, role, permissions, business_id, status, last_login, created_at, created_by, updated_at, updated_by, update_number) ON "Nova".t0021 TO nova_readonly;
REVOKE SELECT (password_hash) ON "Nova".t0021 FROM nova_readonly;

-- Revoke full table SELECT on t0056 (API Keys) and grant only non-credential columns
REVOKE SELECT ON "Nova".t0056 FROM nova_readonly;
GRANT SELECT (id, key_name, client_id, permissions, expires_at, is_active, created_at, created_by, updated_at, updated_by, update_number) ON "Nova".t0056 TO nova_readonly;
REVOKE SELECT (api_key) ON "Nova".t0056 FROM nova_readonly;

-- 5. Grant role membership to current database user so connection pool can SET ROLE
GRANT nova_readonly TO CURRENT_USER;

COMMIT;
