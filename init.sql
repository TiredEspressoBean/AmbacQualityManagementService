-- PostgreSQL Initialization Script
-- 
-- NOTE: For environment variable support, use init.sql.template instead.
-- This file contains default values for development.
--
-- Environment Variables (when using template):
-- - POSTGRES_DB (default: tracker_AMBAC)
-- - POSTGRES_READONLY_USER (default: readonly_user) 
-- - POSTGRES_READONLY_PASSWORD (default: readonly_pw)
--
-- To generate from template:
-- envsubst < init.sql.template > init.sql

-- Create readonly role group (optional but recommended)
CREATE ROLE readonly;

-- Create the readonly user and assign to readonly group  
CREATE USER readonly_user WITH PASSWORD 'readonly_pw';
GRANT readonly TO readonly_user;

-- Grant access to database
GRANT CONNECT ON DATABASE "tracker_AMBAC" TO readonly;

-- Grant schema-level usage
GRANT USAGE ON SCHEMA public TO readonly;

-- Grant table and sequence access for current objects
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO readonly;

-- Grant SELECT for future tables and sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON SEQUENCES TO readonly;
