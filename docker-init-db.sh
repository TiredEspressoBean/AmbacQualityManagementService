#!/bin/bash

# Docker PostgreSQL initialization script
# This script processes the init.sql.template to generate init.sql with environment variables

set -e

echo "Processing PostgreSQL initialization template..."

# Set defaults if environment variables are not provided
export POSTGRES_DB=${POSTGRES_DB:-"tracker_AMBAC"}
export POSTGRES_READONLY_USER=${POSTGRES_READONLY_USER:-"readonly_user"}  
export POSTGRES_READONLY_PASSWORD=${POSTGRES_READONLY_PASSWORD:-"readonly_pw"}

# Check if template exists
if [ -f "/docker-entrypoint-initdb.d/init.sql.template" ]; then
    echo "Found init.sql.template, processing with environment variables..."
    echo "Database: $POSTGRES_DB"
    echo "Readonly user: $POSTGRES_READONLY_USER"
    
    # Process template and output to init.sql
    envsubst < /docker-entrypoint-initdb.d/init.sql.template > /docker-entrypoint-initdb.d/init-processed.sql
    
    echo "Template processed successfully"
else
    echo "No template found, using existing init.sql"
fi