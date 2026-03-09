#!/bin/bash
# Fix pgBackRest permissions on mounted volumes
chown -R postgres:postgres /var/lib/pgbackrest /var/log/pgbackrest /var/spool/pgbackrest 2>/dev/null || true

# Run the original postgres entrypoint
exec docker-entrypoint.sh "$@"