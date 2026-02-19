"""
Management command to enable Row-Level Security (RLS) on tenant-scoped tables.

Usage:
    python manage.py setup_rls [--disable]

RLS provides database-level tenant isolation as a defense-in-depth measure.
Even if application code has a bug, RLS prevents cross-tenant data access.

Requirements:
1. ENABLE_RLS=true in Django settings (or use --force)
2. Django must connect as 'partstracker_app' role (not superuser) for RLS to apply
3. TenantMiddleware must set: SET LOCAL app.current_tenant_id = '<uuid>'
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = 'Enable Row-Level Security on tenant-scoped tables'

    # All tables that have a tenant_id foreign key
    TENANT_SCOPED_TABLES = [
        # Core
        'Tracker_user',
        'Tracker_companies',

        # Approval Workflow
        'Tracker_approvalrequest',
        'Tracker_approvalresponse',
        'Tracker_approvaltemplate',
        'tracker_approver_assignment',
        'tracker_group_approver_assignment',

        # Documents
        'Tracker_documents',
        'Tracker_documenttype',
        'Tracker_generatedreport',

        # Equipment
        'Tracker_equipments',
        'Tracker_equipmenttype',
        'Tracker_equipmentusage',
        'Tracker_calibrationrecord',
        'Tracker_trainingrecord',
        'Tracker_trainingtype',

        # MES Lite - Orders & Parts
        'Tracker_orders',
        'Tracker_parts',
        'Tracker_parttypes',
        'Tracker_workorder',

        # MES Lite - Processes & Steps
        'Tracker_processes',
        'Tracker_steps',
        'Tracker_stepexecution',
        'Tracker_steptransitionlog',

        # QMS - Quality Reports
        'Tracker_qualityreports',
        'Tracker_qualityerrorslist',
        'Tracker_quarantinedisposition',
        'Tracker_qaapproval',

        # QMS - Sampling
        'Tracker_samplingruleset',
        'Tracker_samplingrule',
        'Tracker_samplingauditlog',
        'Tracker_samplingtriggerstate',
        'Tracker_samplinganalytics',
        'Tracker_measurementdefinition',
        'Tracker_measurementresult',

        # QMS - CAPA
        'Tracker_capa',
        'Tracker_capatasks',
        'Tracker_capataskassignee',
        'Tracker_capaverification',
        'Tracker_rcarecord',
        'Tracker_rootcause',
        'Tracker_fivewhys',
        'Tracker_fishbone',

        # QMS - 3D/Heatmap
        'Tracker_threedmodel',
        'Tracker_heatmapannotations',

        # SPC
        'Tracker_spcbaseline',

        # DMS
        'Tracker_chatsession',

        # Misc
        'Tracker_archivereason',
        'Tracker_externalapiorderidentifier',
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--disable',
            action='store_true',
            help='Disable RLS instead of enabling it',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Run even if ENABLE_RLS is False in settings',
        )

    def handle(self, *args, **options):
        if options['disable']:
            self.disable_rls()
        else:
            self.enable_rls(force=options['force'])

    def _find_table(self, cursor, table_name):
        """Find actual table name (case-insensitive search)."""
        cursor.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename ILIKE %s
        """, [table_name])
        result = cursor.fetchone()
        return result[0] if result else None

    def _has_tenant_column(self, cursor, table_name):
        """Check if table has tenant_id column."""
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s
                AND column_name = 'tenant_id'
            )
        """, [table_name])
        return cursor.fetchone()[0]

    def enable_rls(self, force=False):
        """Enable RLS policies on all tenant-scoped tables."""

        if not force and not getattr(settings, 'ENABLE_RLS', False):
            self.stdout.write(
                self.style.WARNING(
                    'ENABLE_RLS is False in settings. Use --force to override.'
                )
            )
            return

        self.stdout.write('Enabling Row-Level Security...')

        enabled_count = 0
        skipped_count = 0

        with connection.cursor() as cursor:
            for table in self.TENANT_SCOPED_TABLES:
                # Find actual table name (handles case sensitivity)
                actual_table = self._find_table(cursor, table)

                if not actual_table:
                    self.stdout.write(f'  Skip (no table): {table}')
                    skipped_count += 1
                    continue

                # Check if tenant_id column exists
                if not self._has_tenant_column(cursor, actual_table):
                    self.stdout.write(f'  Skip (no tenant_id): {actual_table}')
                    skipped_count += 1
                    continue

                # Enable RLS
                cursor.execute(f'ALTER TABLE "{actual_table}" ENABLE ROW LEVEL SECURITY;')
                cursor.execute(f'ALTER TABLE "{actual_table}" FORCE ROW LEVEL SECURITY;')

                # Drop existing policy (idempotent)
                cursor.execute(f'DROP POLICY IF EXISTS tenant_isolation_policy ON "{actual_table}";')

                # Create tenant isolation policy
                cursor.execute(f'''
                    CREATE POLICY tenant_isolation_policy ON "{actual_table}"
                    FOR ALL
                    USING (
                        tenant_id IS NULL
                        OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                    )
                    WITH CHECK (
                        tenant_id IS NULL
                        OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                    );
                ''')

                self.stdout.write(f'  Enabled: {actual_table}')
                enabled_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. Enabled RLS on {enabled_count} tables, skipped {skipped_count}.'
            )
        )

    def disable_rls(self):
        """Disable RLS policies (for development/testing)."""

        self.stdout.write(self.style.WARNING('Disabling Row-Level Security...'))

        disabled_count = 0

        with connection.cursor() as cursor:
            for table in self.TENANT_SCOPED_TABLES:
                actual_table = self._find_table(cursor, table)
                if not actual_table:
                    continue

                try:
                    cursor.execute(f'DROP POLICY IF EXISTS tenant_isolation_policy ON "{actual_table}";')
                    cursor.execute(f'ALTER TABLE "{actual_table}" DISABLE ROW LEVEL SECURITY;')
                    self.stdout.write(f'  Disabled: {actual_table}')
                    disabled_count += 1
                except Exception as e:
                    self.stdout.write(f'  Skip: {actual_table} ({e})')

        self.stdout.write(
            self.style.SUCCESS(f'Done. Disabled RLS on {disabled_count} tables.')
        )
