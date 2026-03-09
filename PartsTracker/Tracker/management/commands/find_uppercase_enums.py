"""
Management command to scan database for uppercase enum values that should be lowercase.

Directly queries the database to find any uppercase values in enum fields.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Scan database for uppercase enum values'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('Scanning for Uppercase Enum Values'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write('')

        # Define tables and fields to check
        # Format: (table_name, field_name)
        checks = [
            # Core
            ('"Tracker_tenant"', 'tier'),
            ('"Tracker_tenant"', 'status'),

            # MES Lite
            ('"Tracker_stepedge"', 'edge_type'),
            ('"Tracker_parts"', 'part_status'),
            ('"Tracker_processes"', 'status'),
            ('"Tracker_orders"', 'status'),
            ('"Tracker_orders"', 'apqp_stage'),
            ('"Tracker_workorder"', 'status'),
            ('"Tracker_workorder"', 'priority'),

            # QMS
            ('"Tracker_qualityreportdefect"', 'severity'),
            ('"Tracker_capa"', 'capa_type'),
            ('"Tracker_capa"', 'severity'),
            ('"Tracker_capa"', 'status'),
            ('"Tracker_capatasks"', 'task_type'),
            ('"Tracker_capatasks"', 'status'),
            ('"Tracker_rcarecord"', 'method'),
            ('"Tracker_rcarecord"', 'review_status'),
            ('"Tracker_rootcause"', 'category'),
            ('"Tracker_rootcause"', 'verification_status'),
            ('"Tracker_fpirecord"', 'status'),
            ('"Tracker_fpirecord"', 'result'),
            ('"Tracker_stepoverride"', 'block_type'),
            ('"Tracker_stepoverride"', 'override_status'),
            ('"Tracker_steprollback"', 'reason'),
            ('"Tracker_steprollback"', 'status'),

            # Equipment
            ('"Tracker_equipments"', 'status'),

            # Step requirements
            ('"Tracker_steprequirement"', 'requirement_type'),
        ]

        total_uppercase = 0

        with connection.cursor() as cursor:
            for table_name, field_name in checks:
                try:
                    # Check if table exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_name = %s
                        )
                    """, [table_name.strip('"')])

                    if not cursor.fetchone()[0]:
                        continue

                    # Check if field exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.columns
                            WHERE table_name = %s AND column_name = %s
                        )
                    """, [table_name.strip('"'), field_name])

                    if not cursor.fetchone()[0]:
                        continue

                    # Find uppercase values
                    # Check for values that contain uppercase letters
                    cursor.execute(f"""
                        SELECT DISTINCT {field_name}, COUNT(*) as count
                        FROM {table_name}
                        WHERE {field_name} IS NOT NULL
                        AND {field_name} != LOWER({field_name})
                        GROUP BY {field_name}
                    """)

                    results = cursor.fetchall()
                    if results:
                        self.stdout.write(self.style.WARNING(f'\n{table_name}.{field_name}:'))
                        for value, count in results:
                            self.stdout.write(f'  Found {count} records with uppercase value: "{value}"')
                            total_uppercase += count

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error checking {table_name}.{field_name}: {str(e)}'))

        # Also check for any specific uppercase patterns we know about
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('Checking for known uppercase patterns'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write('')

        known_uppercase_patterns = [
            'DEFAULT', 'ALTERNATE', 'ESCALATION',  # EdgeType
            'PENDING', 'IN_PROGRESS', 'COMPLETED', 'ON_HOLD', 'CANCELLED',  # Status fields
            'DRAFT', 'APPROVED', 'DEPRECATED',  # ProcessStatus
            'RFI', 'AWAITING_QA',  # OrdersStatus, PartsStatus
            'CORRECTIVE', 'PREVENTIVE', 'CUSTOMER_COMPLAINT',  # CapaType
            'CRITICAL', 'MAJOR', 'MINOR',  # Severity fields
            'WAITING_FOR_OPERATOR',  # WorkOrderStatus
        ]

        pattern_found = False
        for table_name, field_name in checks:
            try:
                with connection.cursor() as cursor:
                    # Check if table exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_name = %s
                        )
                    """, [table_name.strip('"')])

                    if not cursor.fetchone()[0]:
                        continue

                    # Check if field exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.columns
                            WHERE table_name = %s AND column_name = %s
                        )
                    """, [table_name.strip('"'), field_name])

                    if not cursor.fetchone()[0]:
                        continue

                    for pattern in known_uppercase_patterns:
                        cursor.execute(f"""
                            SELECT COUNT(*)
                            FROM {table_name}
                            WHERE {field_name} = %s
                        """, [pattern])
                        count = cursor.fetchone()[0]
                        if count > 0:
                            pattern_found = True
                            self.stdout.write(
                                self.style.ERROR(f'{table_name}.{field_name} has {count} records with "{pattern}"')
                            )

            except Exception as e:
                pass

        if not pattern_found:
            self.stdout.write(self.style.SUCCESS('No known uppercase patterns found'))

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 80))
        if total_uppercase > 0:
            self.stdout.write(self.style.ERROR(f'Found {total_uppercase} records with uppercase enum values'))
        else:
            self.stdout.write(self.style.SUCCESS('No uppercase enum values found'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
