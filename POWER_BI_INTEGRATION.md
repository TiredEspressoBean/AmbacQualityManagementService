# Power BI Integration Guide

This guide covers how to configure PostgreSQL database access for Power BI in both local and Azure deployments.

## Overview

Power BI can connect to your PostgreSQL database to create dashboards and reports from your Parts Tracker data. This guide covers:

1. **Local Development**: Connect Power BI to local PostgreSQL
2. **Linux Production**: Configure secure database access
3. **Azure Production**: Set up Azure PostgreSQL for Power BI
4. **Security Considerations**: Read-only users and network access
5. **Sample Power BI Queries**: Pre-built queries for common reports

## Local Development Setup

### Step 1: Configure Local PostgreSQL for External Access

Update your local `docker-compose.yml` to expose PostgreSQL:

```yaml
services:
  postgres:
    image: postgres:16
    ports:
      - "5432:5432"  # Expose to host for Power BI access
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init-powerbi.sql:/docker-entrypoint-initdb.d/init-powerbi.sql
```

### Step 2: Create Read-Only User for Power BI

Create `init-powerbi.sql`:

```sql
-- Create read-only user for Power BI
CREATE USER powerbi_reader WITH PASSWORD '${POWERBI_PASSWORD}';

-- Grant connection privileges
GRANT CONNECT ON DATABASE parts_tracker_dev TO powerbi_reader;

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO powerbi_reader;

-- Grant select on all tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO powerbi_reader;

-- Grant select on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO powerbi_reader;

-- Grant usage on sequences (for auto-incrementing fields)
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO powerbi_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO powerbi_reader;
```

### Step 3: Power BI Connection Settings (Local)

**Connection Details:**
- **Server**: `localhost` or `127.0.0.1`
- **Port**: `5432`
- **Database**: `parts_tracker_dev`
- **Username**: `powerbi_reader`
- **Password**: `${POWERBI_PASSWORD}` (from environment)
- **Connection Type**: `DirectQuery` (recommended for live data)

## Linux Production Setup

### Step 1: Configure PostgreSQL for Remote Access

Update PostgreSQL configuration in your Linux deployment:

```bash
# Create PowerBI user setup script
cat > setup-powerbi-user.sh << 'EOF'
#!/bin/bash
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U parts_tracker_user -d parts_tracker_prod << EOSQL
-- Create read-only user for Power BI
CREATE USER powerbi_reader WITH PASSWORD '\${POWERBI_PASSWORD}';

-- Grant connection privileges
GRANT CONNECT ON DATABASE parts_tracker_prod TO powerbi_reader;

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO powerbi_reader;

-- Grant select on all tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO powerbi_reader;

-- Grant select on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO powerbi_reader;

-- Grant usage on sequences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO powerbi_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO powerbi_reader;

-- Create specific views for Power BI (optional)
CREATE OR REPLACE VIEW powerbi_parts_summary AS
SELECT 
    p.id,
    p.part_number,
    p.description,
    pt.name as part_type,
    p.status,
    p.created_at,
    p.updated_at,
    o.order_number,
    o.customer_id,
    c.name as customer_name
FROM parts p
LEFT JOIN part_types pt ON p.part_type_id = pt.id
LEFT JOIN orders o ON p.order_id = o.id
LEFT JOIN customers c ON o.customer_id = c.id;

-- Grant access to the view
GRANT SELECT ON powerbi_parts_summary TO powerbi_reader;
EOSQL
EOF

chmod +x setup-powerbi-user.sh
./setup-powerbi-user.sh
```

### Step 2: Configure Network Access

Update your `docker-compose.prod.yml` to allow external connections:

```yaml
services:
  postgres:
    image: postgres:16
    ports:
      - "5432:5432"  # Expose for Power BI access
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata_prod:/var/lib/postgresql/data
      - ./postgresql.conf:/etc/postgresql/postgresql.conf
      - ./pg_hba.conf:/etc/postgresql/pg_hba.conf
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

Create `postgresql.conf`:
```conf
# PostgreSQL configuration for Power BI access
listen_addresses = '*'
port = 5432
max_connections = 100
shared_buffers = 128MB
effective_cache_size = 256MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 4.0
effective_io_concurrency = 2
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_statement = 'all'
log_min_duration_statement = 1000

# Security
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
```

Create `pg_hba.conf`:
```conf
# PostgreSQL Client Authentication Configuration

# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     trust

# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
host    all             all             172.16.0.0/12           md5  # Docker networks

# Power BI access (adjust IP ranges for your network)
host    parts_tracker_prod  powerbi_reader  YOUR_OFFICE_IP/32   md5
host    parts_tracker_prod  powerbi_reader  YOUR_VPN_RANGE/24   md5

# Deny all other connections
host    all             all             0.0.0.0/0               reject
```

### Step 3: Configure Firewall

```bash
# Allow PostgreSQL access from specific IPs
sudo ufw allow from YOUR_OFFICE_IP to any port 5432
sudo ufw allow from YOUR_VPN_RANGE to any port 5432

# Or allow from specific network range
sudo ufw allow from 10.0.0.0/8 to any port 5432
```

### Step 4: Power BI Connection Settings (Linux Production)

**Connection Details:**
- **Server**: `YOUR_LINUX_SERVER_IP`
- **Port**: `5432`
- **Database**: `parts_tracker_prod`
- **Username**: `powerbi_reader`
- **Password**: `${POWERBI_PASSWORD}` (from environment)
- **Connection Type**: `DirectQuery`

## Azure Production Setup

### Step 1: Configure Azure PostgreSQL for Power BI

Update your Azure deployment to include Power BI access:

```bash
# Create read-only user in Azure PostgreSQL
az postgres flexible-server execute \
  --name $POSTGRES_SERVER \
  --admin-user parts_tracker_user \
  --admin-password $POSTGRES_PASSWORD \
  --database-name parts_tracker \
  --querytext "
    CREATE USER powerbi_reader WITH PASSWORD '\${POWERBI_PASSWORD}';
    GRANT CONNECT ON DATABASE parts_tracker TO powerbi_reader;
    GRANT USAGE ON SCHEMA public TO powerbi_reader;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO powerbi_reader;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO powerbi_reader;
    GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO powerbi_reader;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO powerbi_reader;
  "
```

### Step 2: Configure Azure PostgreSQL Firewall

```bash
# Allow Power BI service IP ranges (these change, check Microsoft docs)
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_SERVER \
  --rule-name AllowPowerBIService \
  --start-ip-address 52.136.0.0 \
  --end-ip-address 52.136.255.255

# Allow your office/development IP
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_SERVER \
  --rule-name AllowOfficeIP \
  --start-ip-address YOUR_OFFICE_IP \
  --end-ip-address YOUR_OFFICE_IP

# Allow Azure services (for Container Apps)
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_SERVER \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### Step 3: Power BI Connection Settings (Azure)

**Connection Details:**
- **Server**: `your-postgres-server.postgres.database.azure.com`
- **Port**: `5432`
- **Database**: `parts_tracker`
- **Username**: `powerbi_reader`
- **Password**: `${POWERBI_PASSWORD}` (from environment)
- **Connection Type**: `DirectQuery`
- **Encryption**: `Required` (SSL)

## Power BI Connection Setup

### Step 1: Install PostgreSQL Connector

1. Open **Power BI Desktop**
2. Go to **File** > **Options and settings** > **Options**
3. Select **Preview features**
4. Enable **PostgreSQL connector** (if not already enabled)

### Step 2: Connect to Database

1. In Power BI Desktop, click **Get Data**
2. Select **Database** > **PostgreSQL database**
3. Enter connection details:
   - **Server**: (see environment-specific settings above)
   - **Database**: (see environment-specific settings above)
4. Click **OK**
5. Select **Database** authentication
6. Enter **Username** and **Password** for `powerbi_reader`
7. Click **Connect**

### Step 3: Select Tables and Views

Choose from available tables:
- `parts` - Individual part records
- `orders` - Order information
- `customers` - Customer data
- `part_types` - Part type classifications
- `quality_reports` - Quality control data
- `work_orders` - Work order tracking
- `powerbi_parts_summary` - Pre-built summary view

## Security Best Practices

### Database Security

1. **Use Read-Only User**: Never use admin credentials for Power BI
2. **Limit Network Access**: Configure firewall rules strictly
3. **Use SSL**: Enable SSL connections for production
4. **Regular Password Rotation**: Change Power BI user password regularly

```sql
-- Rotate Power BI user password
ALTER USER powerbi_reader WITH PASSWORD '${NEW_POWERBI_PASSWORD}';
```

### Network Security

1. **Whitelist IPs**: Only allow specific IP addresses
2. **Use VPN**: Connect through corporate VPN when possible
3. **Monitor Access**: Enable PostgreSQL logging

```bash
# Monitor PostgreSQL connections
docker-compose -f docker-compose.prod.yml logs postgres | grep "connection"

# Check active connections
docker-compose -f docker-compose.prod.yml exec postgres psql -U parts_tracker_user -d parts_tracker_prod -c "SELECT * FROM pg_stat_activity WHERE usename = 'powerbi_reader';"
```

## Sample Power BI Queries

### Parts Status Dashboard

```sql
-- Parts by Status
SELECT 
    status,
    COUNT(*) as part_count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM parts 
GROUP BY status;

-- Parts by Month
SELECT 
    DATE_TRUNC('month', created_at) as month,
    COUNT(*) as parts_created
FROM parts 
WHERE created_at >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month;
```

### Quality Metrics

```sql
-- Quality Reports Summary
SELECT 
    p.part_number,
    p.description,
    qr.measurement,
    qr.result,
    qr.created_at,
    CASE 
        WHEN qr.result = 'PASS' THEN 1 
        ELSE 0 
    END as pass_flag
FROM quality_reports qr
JOIN parts p ON qr.part_id = p.id
WHERE qr.created_at >= CURRENT_DATE - INTERVAL '30 days';
```

### Customer Analysis

```sql
-- Customer Order Summary
SELECT 
    c.name as customer_name,
    COUNT(DISTINCT o.id) as total_orders,
    COUNT(p.id) as total_parts,
    AVG(CASE WHEN p.status = 'COMPLETED' THEN 1.0 ELSE 0.0 END) as completion_rate
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
LEFT JOIN parts p ON o.id = p.order_id
GROUP BY c.id, c.name
ORDER BY total_orders DESC;
```

## Troubleshooting

### Connection Issues

```bash
# Test database connection from Power BI machine
psql -h YOUR_SERVER_IP -p 5432 -U powerbi_reader -d parts_tracker_prod

# Check PostgreSQL logs
docker-compose -f docker-compose.prod.yml logs postgres

# Verify user permissions
docker-compose -f docker-compose.prod.yml exec postgres psql -U parts_tracker_user -d parts_tracker_prod -c "\du powerbi_reader"
```

### Performance Issues

1. **Use DirectQuery**: For real-time data with large datasets
2. **Import Mode**: For smaller datasets that don't change frequently
3. **Create Indexes**: Add database indexes for Power BI queries

```sql
-- Create indexes for common Power BI queries
CREATE INDEX idx_parts_status ON parts(status);
CREATE INDEX idx_parts_created_at ON parts(created_at);
CREATE INDEX idx_quality_reports_created_at ON quality_reports(created_at);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
```

### Firewall Issues

```bash
# Check if port is open
telnet YOUR_SERVER_IP 5432

# Check firewall rules (Linux)
sudo ufw status

# Check PostgreSQL is listening
sudo netstat -tlnp | grep 5432
```

## Maintenance

### Regular Tasks

1. **Update Firewall Rules**: When IP addresses change
2. **Rotate Passwords**: Monthly password changes
3. **Monitor Performance**: Check query performance
4. **Update Statistics**: Keep PostgreSQL statistics current

```sql
-- Update table statistics for better query planning
ANALYZE;

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

This comprehensive guide ensures secure and efficient Power BI integration with your Parts Tracker database across all deployment environments.