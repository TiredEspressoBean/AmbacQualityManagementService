"""
Management command to enable required PostgreSQL extensions.

Usage:
    python manage.py setup_extensions

Enables:
- pgvector: Vector similarity search for AI embeddings
- pg_trgm: Trigram matching for fuzzy text search (optional)
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
                            '      Install with: apt install postgresql-16-pgvector (or similar)'
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'  [FAIL] {ext_name} - {e}')
                        )

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(f'Enabled {enabled_count} extensions.')
        )
