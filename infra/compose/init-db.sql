-- S-019: Three-role DB architecture for compose parity with CI.
-- Run at PostgreSQL container initialisation (mounted to /docker-entrypoint-initdb.d/).
-- Idempotent — safe to re-run (IF NOT EXISTS guards).

-- =========================================================================
-- 1. App runtime role — NOBYPASSRLS, strictly DML-only
-- =========================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'retail_media_app') THEN
        CREATE ROLE retail_media_app LOGIN PASSWORD 'retail_media_app_pass'
            NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE retail_media_platform TO retail_media_app;
GRANT USAGE ON SCHEMA public TO retail_media_app;

-- Future tables created by migrations get these privileges automatically
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO retail_media_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO retail_media_app;

-- =========================================================================
-- 2. Grant on existing tables (no-op at container bootstrap — tables created
--    later by migrations; post-migration grant in db-setup covers those)
-- =========================================================================
DO $$
BEGIN
    RAISE NOTICE 'init-db.sql: retail_media_app role created. '
        'Post-migration grants handled by db-setup service.';
END
$$;
