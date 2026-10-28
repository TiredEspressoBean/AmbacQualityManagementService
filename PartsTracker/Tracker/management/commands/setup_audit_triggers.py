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
        ('Tracker_capastatustransition', 'capa_transition_immutable'),
        ('Tracker_recordedit', 'record_edit_immutable'),
    ]

    # An approval response is a signature, but one the approver may still withdraw or
    # delegate while the request is open, and answer again after withdrawing (one row
    # per approver; each change also lands in RecordEdit and the audit log, both
    # immutable). So its trigger admits exactly those moves and nothing else: a
    # signed answer's content never changes in place, and no response is deleted.
    RESPONSE_TABLE = ('Tracker_approvalresponse', 'approval_response_immutable')

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

            enabled_count += self._enable_response_trigger(cursor)

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. Created {enabled_count} immutability triggers.'
            )
        )

    def _enable_response_trigger(self, cursor):
        table_name, trigger_name = self.RESPONSE_TABLE
        actual_table = self._table_exists(cursor, table_name)
        if not actual_table:
            self.stdout.write(f'  Skip (no table): {table_name}')
            return 0
        cursor.execute("""
            CREATE OR REPLACE FUNCTION guard_approval_response() RETURNS TRIGGER AS $$
            BEGIN
                IF TG_OP = 'UPDATE'
                   AND NEW.id = OLD.id
                   AND NEW.tenant_id = OLD.tenant_id
                   AND NEW.approval_request_id = OLD.approval_request_id
                   AND NEW.approver_id = OLD.approver_id
                   AND NEW.created_at = OLD.created_at
                   AND NEW.archived = OLD.archived
                   AND NEW.deleted_at IS NOT DISTINCT FROM OLD.deleted_at
                THEN
                    -- Answering again after a withdrawal: a new signature in full.
                    IF OLD.decision = 'WITHDRAWN' AND NEW.decision IN ('APPROVED', 'REJECTED') THEN
                        RETURN NEW;
                    END IF;
                    -- Withdrawing (only the decision moves) or delegating (decision,
                    -- delegatee and the reason): the signature itself stays as given.
                    IF NEW.signature_data IS NOT DISTINCT FROM OLD.signature_data
                       AND NEW.signature_meaning IS NOT DISTINCT FROM OLD.signature_meaning
                       AND NEW.verified_at IS NOT DISTINCT FROM OLD.verified_at
                       AND NEW.verification_method = OLD.verification_method
                       AND NEW.ip_address IS NOT DISTINCT FROM OLD.ip_address
                       AND NEW.self_approved = OLD.self_approved
                       AND NEW.decision_date = OLD.decision_date
                    THEN
                        IF OLD.decision IN ('APPROVED', 'REJECTED') AND NEW.decision = 'WITHDRAWN'
                           AND NEW.comments IS NOT DISTINCT FROM OLD.comments
                           AND NEW.delegated_to_id IS NOT DISTINCT FROM OLD.delegated_to_id THEN
                            RETURN NEW;
                        END IF;
                        IF OLD.decision <> 'DELEGATED' AND NEW.decision = 'DELEGATED' THEN
                            RETURN NEW;
                        END IF;
                    END IF;
                END IF;
                RAISE EXCEPTION 'COMPLIANCE VIOLATION: An approval response can only be '
                    'withdrawn, delegated, or answered again after withdrawal. '
                    'Attempted operation: % on table: %.', TG_OP, TG_TABLE_NAME;
            END;
            $$ LANGUAGE plpgsql;
        """)
        cursor.execute(f'DROP TRIGGER IF EXISTS {trigger_name} ON "{actual_table}";')
        cursor.execute(f"""
            CREATE TRIGGER {trigger_name}
                BEFORE UPDATE OR DELETE ON "{actual_table}"
                FOR EACH ROW
                EXECUTE FUNCTION guard_approval_response();
        """)
        self.stdout.write(f'  Created trigger: {trigger_name} on {actual_table}')
        return 1

    def disable_triggers(self):
        """Remove immutability triggers (for development/testing only)."""

        self.stdout.write(
            self.style.WARNING('Removing audit immutability triggers...')
        )

        with connection.cursor() as cursor:
            disabled_count = 0
            for table_name, trigger_name in [*self.AUDIT_TABLES, self.RESPONSE_TABLE]:
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
            cursor.execute('DROP FUNCTION IF EXISTS guard_approval_response();')
            self.stdout.write('  Dropped function: prevent_audit_modification()')

        self.stdout.write(
            self.style.SUCCESS(f'Done. Removed {disabled_count} triggers.')
        )
