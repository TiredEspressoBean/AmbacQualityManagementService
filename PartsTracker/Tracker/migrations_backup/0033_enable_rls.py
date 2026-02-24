# Generated migration for Row-Level Security policies
"""
Enable Row-Level Security (RLS) on all tenant-scoped tables.

RLS provides database-level tenant isolation as a defense-in-depth measure.
Even if application code has a bug, RLS prevents cross-tenant data access.

Requirements:
1. ENABLE_RLS=true in Django settings
2. Django must connect as 'partstracker_app' role (not superuser)
3. TenantMiddleware must set: SET LOCAL app.current_tenant_id = '<uuid>'

To enable:
1. Run this migration: python manage.py migrate
2. Set ENABLE_RLS=true in .env
3. Optionally switch Django to use partstracker_app role
"""

from django.db import migrations
from django.conf import settings


# All tables that have a tenant_id foreign key (from migration 0032)
TENANT_SCOPED_TABLES = [
    # Core
    'Tracker_user',
    'Tracker_companies',

    # Approval Workflow
    'Tracker_approvalrequest',
    'Tracker_approvalresponse',
    'Tracker_approvaltemplate',

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


def enable_rls(apps, schema_editor):
    """Enable RLS policies on all tenant-scoped tables."""

    # Skip if RLS is not enabled in settings
    if not getattr(settings, 'ENABLE_RLS', False):
        print("\n  ENABLE_RLS is False - skipping RLS policy creation.")
        print("  Set ENABLE_RLS=true in settings to enable database-level isolation.\n")
        return

    connection = schema_editor.connection

    for table in TENANT_SCOPED_TABLES:
        # Check if table exists (some may not exist in all environments)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                )
            """, [table.lower()])
            exists = cursor.fetchone()[0]

            if not exists:
                print(f"  Skipping {table} (table does not exist)")
                continue

            # Check if tenant_id column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = %s
                    AND column_name = 'tenant_id'
                )
            """, [table.lower()])
            has_tenant = cursor.fetchone()[0]

            if not has_tenant:
                print(f"  Skipping {table} (no tenant_id column)")
                continue

        # Enable RLS on the table
        schema_editor.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;')

        # Force RLS even for table owner (important for superuser connections)
        schema_editor.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY;')

        # Drop existing policy if it exists (for idempotency)
        schema_editor.execute(f'''
            DROP POLICY IF EXISTS tenant_isolation_policy ON "{table}";
        ''')

        # Create the tenant isolation policy
        # - NULL tenant_id: Allow (legacy data or global records)
        # - Matching tenant_id: Allow
        # - No session variable set: Only see NULL tenant_id records
        schema_editor.execute(f'''
            CREATE POLICY tenant_isolation_policy ON "{table}"
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

        print(f"  Enabled RLS on {table}")


def disable_rls(apps, schema_editor):
    """Disable RLS policies (reverse migration)."""

    for table in TENANT_SCOPED_TABLES:
        try:
            # Drop the policy
            schema_editor.execute(f'''
                DROP POLICY IF EXISTS tenant_isolation_policy ON "{table}";
            ''')

            # Disable RLS
            schema_editor.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY;')

            print(f"  Disabled RLS on {table}")
        except Exception as e:
            # Table might not exist in reverse migration
            print(f"  Skipping {table}: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0032_tenant_tenantgroupmembership_and_more'),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
