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
