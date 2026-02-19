#!/bin/bash
# Resets the PostgreSQL database for local development.

set -e

echo -e "\nResetting database..."

# Stop and remove postgres container
docker stop partstracker-postgres 2>/dev/null || true
docker rm partstracker-postgres 2>/dev/null || true

# Remove volume
docker volume rm partstracker_pgdata 2>/dev/null || true

echo "Removed old container and data"

# Restart using setup script
"$(dirname "$0")/setup-dev.sh"
