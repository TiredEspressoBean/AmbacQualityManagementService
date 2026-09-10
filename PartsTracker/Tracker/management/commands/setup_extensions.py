"""
Management command to enable required PostgreSQL extensions.

Usage:
    python manage.py setup_extensions

Enables:
- pgvector: Vector similarity search for AI embeddings
- pg_trgm: Trigram matching for fuzzy text search (optional)

Also sets the pgvector query-time settings at database scope, so they survive
reconnects and apply to Django, Celery and psql alike without per-query code.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Enable required PostgreSQL extensions'

    # Extensions to enable
    EXTENSIONS = [
        ('vector', 'pgvector - Vector similarity search for AI embeddings'),
        ('pg_trgm', 'pg_trgm - Trigram matching for fuzzy text search'),
    ]

    # pgvector query-time settings, applied with ALTER DATABASE so they hold for
    # every new connection rather than needing a SET at each call site.
    VECTOR_SETTINGS = [
        (
            'hnsw.iterative_scan',
            'relaxed_order',
            "Semantic search filters (for_user() scoping, a distance bound) are "
            "applied AFTER the index returns candidates. With iterative_scan off "
            "-- the default -- pgvector pulls ~ef_search rows once, filters them, "
            "and returns whatever survives, so a selective filter silently yields "
            "fewer rows than LIMIT asked for and reads as 'nothing relevant "
            "found'. Iterative scan keeps scanning until the limit is met. "
            "relaxed_order allows slight reordering for speed; strict_order "
            "guarantees exact distance order at more cost.",
        ),
        (
            'hnsw.ef_search',
            '100',
            "Candidate list size per query (default 40). Retrieval feeding an LLM "
            "wants recall over microseconds, and these queries pull a top-10 that "
            "gets read in full, so a wider search is worth the latency.",
        ),
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='Only check which extensions are installed',
        )

    def handle(self, *args, **options):
        if options['check']:
            self.check_extensions()
        else:
            self.enable_extensions()

    def check_extensions(self):
        """Check which extensions are installed."""
        self.stdout.write('Checking PostgreSQL extensions...\n')

        with connection.cursor() as cursor:
            for ext_name, description in self.EXTENSIONS:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM pg_extension WHERE extname = %s
                    )
                """, [ext_name])
                installed = cursor.fetchone()[0]

                status = self.style.SUCCESS('installed') if installed else self.style.WARNING('not installed')
                self.stdout.write(f'  {ext_name}: {status}')
                self.stdout.write(f'    {description}')

            self.stdout.write('')
            self.stdout.write('pgvector query settings (database scope):')
            cursor.execute(
                "SELECT unnest(setconfig) FROM pg_db_role_setting s "
                "JOIN pg_database d ON d.oid = s.setdatabase "
                "WHERE d.datname = %s",
                [connection.settings_dict['NAME']],
            )
            applied = dict(
                row[0].split('=', 1) for row in cursor.fetchall() if '=' in row[0]
            )
            for guc, value, _why in self.VECTOR_SETTINGS:
                current = applied.get(guc)
                if current == value:
                    self.stdout.write(self.style.SUCCESS(f'  {guc} = {current}'))
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  {guc} = {current or "unset"} (expected {value})'
                        )
                    )

    def enable_extensions(self):
        """Enable required extensions."""
        self.stdout.write('Enabling PostgreSQL extensions...\n')

        enabled_count = 0
        with connection.cursor() as cursor:
            for ext_name, description in self.EXTENSIONS:
                try:
                    # CREATE EXTENSION IF NOT EXISTS is idempotent
                    cursor.execute(f'CREATE EXTENSION IF NOT EXISTS {ext_name};')

                    # Verify it was created
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM pg_extension WHERE extname = %s
                        )
                    """, [ext_name])
                    installed = cursor.fetchone()[0]

                    if installed:
                        self.stdout.write(self.style.SUCCESS(f'  [OK] {ext_name}'))
                        enabled_count += 1
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'  [FAIL] {ext_name} - failed to create')
                        )

                except Exception as e:
                    # Common error: extension not available (needs to be installed on server)
                    if 'could not open extension control file' in str(e):
                        self.stdout.write(
                            self.style.WARNING(f'  [SKIP] {ext_name} - not available on server')
                        )
                        self.stdout.write(
                            '      Install with: apt install postgresql-17-pgvector (or similar)'
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'  [FAIL] {ext_name} - {e}')
                        )

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(f'Enabled {enabled_count} extensions.')
        )

        self.configure_vector_settings()

    def configure_vector_settings(self):
        """Set pgvector's query-time settings at database scope.

        Skipped when pgvector is absent -- the settings would be inert and the
        message misleading. Note these take effect for NEW connections: an
        already-open Django or Celery connection keeps the old values until it
        is recycled, so a deploy picks them up but a long-lived shell may not.
        """
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS (SELECT FROM pg_extension WHERE extname = 'vector')"
            )
            if not cursor.fetchone()[0]:
                self.stdout.write('')
                self.stdout.write(
                    self.style.WARNING(
                        '  [SKIP] pgvector settings - extension not installed'
                    )
                )
                return

            db_name = connection.ops.quote_name(connection.settings_dict['NAME'])
            self.stdout.write('')
            self.stdout.write('Configuring pgvector query settings...')
            for guc, value, _why in self.VECTOR_SETTINGS:
                # ALTER DATABASE ... SET takes neither placeholders nor a quoted
                # GUC name; guc/value come from the constant above, not input.
                cursor.execute(f"ALTER DATABASE {db_name} SET {guc} = '{value}'")
                self.stdout.write(
                    self.style.SUCCESS(f'  [OK] {guc} = {value}')
                )
