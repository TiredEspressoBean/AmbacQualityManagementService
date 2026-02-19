-- =============================================================================
-- PostgreSQL Initialization Script for PartsTracker
-- Runs ONCE on first database creation via docker-entrypoint-initdb.d
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Multi-Tenancy: App Role for Row-Level Security
-- =============================================================================
--
-- This role is used by the Django application for normal operations.
-- Unlike the postgres superuser, this role is SUBJECT to RLS policies,
-- providing database-level tenant isolation.
--
-- The password should be set via PARTSTRACKER_APP_PASSWORD environment variable.
-- Default is for development only - CHANGE IN PRODUCTION!

DO $$
DECLARE
    app_password TEXT := COALESCE(
        current_setting('app.partstracker_app_password', true),
        'dev_app_password_CHANGE_ME'
    );
BEGIN
    -- Create role if it doesn't exist
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'partstracker_app') THEN
        EXECUTE format('CREATE ROLE partstracker_app LOGIN PASSWORD %L', app_password);
        RAISE NOTICE 'Created partstracker_app role';
    END IF;
END
$$;

-- Grant schema access
GRANT USAGE ON SCHEMA public TO partstracker_app;

-- Grant table permissions (runs on existing tables)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO partstracker_app;

-- Grant sequence permissions (for auto-increment/serial fields)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO partstracker_app;

-- Grant permissions on future objects (tables created by migrations)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO partstracker_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO partstracker_app;

-- =============================================================================
-- Notes for Production
-- =============================================================================
--
-- 1. Set PARTSTRACKER_APP_PASSWORD in your environment before first run
--
-- 2. To enable RLS in Django, set ENABLE_RLS=true in your .env file
--    and configure Django to use partstracker_app for the default connection
--
-- 3. For migrations, keep using the postgres superuser (bypasses RLS)
--
-- 4. This script only runs on NEW databases. For existing deployments:
--    psql -U postgres -d tracker_AMBAC -f init-db.sql
