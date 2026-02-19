"""
Management command to create audit immutability triggers.

Usage:
    python manage.py setup_audit_triggers [--disable]

Creates PostgreSQL triggers that prevent UPDATE and DELETE operations
on audit-related tables, ensuring compliance with:
- NIST 800-171 3.3.8 (Protect audit information)
- SOC 2 CC7.2 (Security incident detection)
- AS9100D traceability requirements

Once applied, audit records cannot be modified or deleted, even by superusers.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Create immutability triggers on audit tables'

    # Tables that should have immutability triggers
    # Format: (table_name, trigger_name)
    # Note: Django creates tables as {AppName}_{modelname} with mixed case
    AUDIT_TABLES = [
        ('auditlog_logentry', 'audit_log_immutable'),
        ('Tracker_permissionchangelog', 'permission_log_immutable'),
        ('Tracker_steptransitionlog', 'transition_log_immutable'),
        ('Tracker_samplingauditlog', 'sampling_log_immutable'),
        ('Tracker_equipmentusage', 'equipment_usage_immutable'),
        ('Tracker_approvalresponse', 'approval_response_immutable'),
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--disable',
            action='store_true',
            help='Remove immutability triggers (development only)',
        )

    def handle(self, *args, **options):
        if options['disable']:
            self.disable_triggers()
        else:
            self.enable_triggers()

    def _table_exists(self, cursor, table_name):
        """Check if a table exists (case-insensitive check first, then exact)."""
        # First check case-insensitive
        cursor.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename ILIKE %s
        """, [table_name])
        result = cursor.fetchone()
        return result[0] if result else None

    def enable_triggers(self):
        """Create immutability triggers on audit tables."""

        self.stdout.write('Creating audit immutability triggers...')

        with connection.cursor() as cursor:
            # Create the trigger function
            cursor.execute("""
                CREATE OR REPLACE FUNCTION prevent_audit_modification()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'COMPLIANCE VIOLATION: Audit records are immutable. '
                        'Attempted operation: % on table: %. '
                        'This action has been blocked and logged.',
                        TG_OP, TG_TABLE_NAME;
                END;
                $$ LANGUAGE plpgsql;
            """)

            cursor.execute("""
                COMMENT ON FUNCTION prevent_audit_modification() IS
                    'Blocks UPDATE/DELETE on audit tables for NIST 800-171 compliance';
            """)

            self.stdout.write('  Created trigger function: prevent_audit_modification()')

            # Create triggers on each audit table
            enabled_count = 0
            for table_name, trigger_name in self.AUDIT_TABLES:
                # Find the actual table name (handles case sensitivity)
                actual_table = self._table_exists(cursor, table_name)

                if not actual_table:
                    self.stdout.write(f'  Skip (no table): {table_name}')
                    continue

                # Drop existing trigger (idempotent)
                # Use quoted identifier for case-sensitive table name
                cursor.execute(f'DROP TRIGGER IF EXISTS {trigger_name} ON "{actual_table}";')

                # Create trigger
                cursor.execute(f"""
                    CREATE TRIGGER {trigger_name}
                        BEFORE UPDATE OR DELETE ON "{actual_table}"
                        FOR EACH ROW
                        EXECUTE FUNCTION prevent_audit_modification();
                """)

                self.stdout.write(f'  Created trigger: {trigger_name} on {actual_table}')
                enabled_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. Created {enabled_count} immutability triggers.'
            )
        )

    def disable_triggers(self):
        """Remove immutability triggers (for development/testing only)."""

        self.stdout.write(
            self.style.WARNING('Removing audit immutability triggers...')
        )

        with connection.cursor() as cursor:
            disabled_count = 0
            for table_name, trigger_name in self.AUDIT_TABLES:
                actual_table = self._table_exists(cursor, table_name)
                if not actual_table:
                    continue

                try:
                    cursor.execute(f'DROP TRIGGER IF EXISTS {trigger_name} ON "{actual_table}";')
                    self.stdout.write(f'  Dropped: {trigger_name}')
                    disabled_count += 1
                except Exception as e:
                    self.stdout.write(f'  Skip: {trigger_name} ({e})')

            # Optionally drop the function
            cursor.execute('DROP FUNCTION IF EXISTS prevent_audit_modification();')
            self.stdout.write('  Dropped function: prevent_audit_modification()')

        self.stdout.write(
            self.style.SUCCESS(f'Done. Removed {disabled_count} triggers.')
        )
