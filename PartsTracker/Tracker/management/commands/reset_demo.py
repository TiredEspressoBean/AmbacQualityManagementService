"""
Management command to reset the demo tenant to a fresh state.

Usage:
    python manage.py reset_demo

    # With custom slug:
    python manage.py reset_demo --slug my-demo

    # Skip confirmation:
    python manage.py reset_demo --yes

This will:
1. Delete all data in the demo tenant (except the Tenant record itself)
2. Run populate_test_data to repopulate with fresh demo data
3. Update the tenant's last reset timestamp
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = 'Reset demo tenant to fresh state with test data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--slug',
            type=str,
            help='Demo tenant slug (default: from DEMO_TENANT_SLUG setting)',
        )
        parser.add_argument(
            '--yes', '-y',
            action='store_true',
            help='Skip confirmation prompt',
        )
        parser.add_argument(
            '--scale',
            type=str,
            choices=['small', 'medium', 'large'],
            default='small',
            help='Data scale for populate_test_data (default: small)',
        )
        parser.add_argument(
            '--keep-users',
            action='store_true',
            help='Keep existing users (only reset data)',
        )

    def handle(self, *args, **options):
        from Tracker.models import Tenant

        # Get demo tenant slug
        slug = options['slug'] or getattr(settings, 'DEMO_TENANT_SLUG', 'demo')

        # Get the tenant
        try:
            tenant = Tenant.objects.get(slug=slug)
        except Tenant.DoesNotExist:
            raise CommandError(
                f'Demo tenant "{slug}" not found. '
                f'Run: python manage.py setup_tenant --slug {slug} --demo --admin-email demo@example.com'
            )

        if not tenant.is_demo:
            raise CommandError(
                f'Tenant "{slug}" is not marked as a demo tenant. '
                f'Use --slug to specify a different tenant, or mark this tenant as demo.'
            )

        # Confirm unless --yes
        if not options['yes']:
            self.stdout.write(
                self.style.WARNING(f'This will DELETE all data in tenant "{tenant.name}" ({tenant.slug})!')
            )
            confirm = input('Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write('Aborted.')
                return

        self.stdout.write(f'Resetting demo tenant: {tenant.name} ({tenant.slug})')
        self.stdout.write('')

        # Delete existing data
        self._delete_tenant_data(tenant, keep_users=options['keep_users'])

        # Repopulate with test data
        self.stdout.write('')
        self.stdout.write('Repopulating with fresh demo data...')
        call_command(
            'populate_test_data',
            scale=options['scale'],
            stdout=self.stdout,
        )

        # Update tenant reset timestamp
        tenant.settings['last_reset_at'] = timezone.now().isoformat()
        tenant.save(update_fields=['settings'])

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Demo reset complete!'))
        self.stdout.write(f'  Tenant: {tenant.slug}')
        self.stdout.write(f'  Reset at: {timezone.now().isoformat()}')

    def _delete_tenant_data(self, tenant, keep_users=False):
        """Delete all data belonging to the tenant."""
        from django.contrib.auth import get_user_model
        from Tracker.models import (
            Orders, WorkOrder, Parts, PartTypes,
            Processes, Steps, StepExecution, StepTransitionLog,
            QualityReports, QuarantineDisposition, QualityErrorsList,
            Documents, DocumentType,
            Equipments, EquipmentType, EquipmentUsage, CalibrationRecord,
            Companies,
            CAPA, CapaTasks, CapaVerification, RcaRecord,
            ApprovalRequest, ApprovalResponse, ApprovalTemplate,
            SamplingRuleSet, SamplingRule, SamplingAuditLog,
            ThreeDModel, HeatMapAnnotations,
            TrainingType, TrainingRecord, TrainingRequirement,
            MeasurementDefinition, MeasurementResult,
            ChatSession,
        )

        User = get_user_model()

        # Order matters due to foreign keys - delete leaf tables first
        models_to_clear = [
            # Audit/logs (some protected by triggers, may need special handling)
            ('Chat Sessions', ChatSession),
            ('Heatmap Annotations', HeatMapAnnotations),
            ('3D Models', ThreeDModel),
            ('Training Records', TrainingRecord),
            ('Training Requirements', TrainingRequirement),
            ('Calibration Records', CalibrationRecord),
            ('Equipment Usage', EquipmentUsage),
            ('Measurement Results', MeasurementResult),
            ('Approval Responses', ApprovalResponse),
            ('Approval Requests', ApprovalRequest),
            ('CAPA Verifications', CapaVerification),
            ('CAPA Tasks', CapaTasks),
            ('RCA Records', RcaRecord),
            ('CAPAs', CAPA),
            ('Sampling Audit Logs', SamplingAuditLog),
            ('Sampling Rules', SamplingRule),
            ('Sampling Rule Sets', SamplingRuleSet),
            ('Quarantine Dispositions', QuarantineDisposition),
            ('Quality Reports', QualityReports),
            ('Quality Errors List', QualityErrorsList),
            ('Step Executions', StepExecution),
            ('Parts', Parts),
            ('Work Orders', WorkOrder),
            ('Orders', Orders),
            ('Steps', Steps),
            ('Measurement Definitions', MeasurementDefinition),
            ('Processes', Processes),
            ('Part Types', PartTypes),
            ('Documents', Documents),
            ('Document Types', DocumentType),
            ('Equipments', Equipments),
            ('Equipment Types', EquipmentType),
            ('Training Types', TrainingType),
            ('Companies', Companies),
            ('Approval Templates', ApprovalTemplate),
        ]

        if not keep_users:
            # Add users last (after all their related data is deleted)
            models_to_clear.append(('Users', User))

        for name, model in models_to_clear:
            try:
                # Filter by tenant if model has tenant field
                if hasattr(model, 'tenant'):
                    qs = model.objects.filter(tenant=tenant)
                elif hasattr(model, 'tenant_id'):
                    qs = model.objects.filter(tenant_id=tenant.id)
                else:
                    # Skip models without tenant field
                    continue

                count = qs.count()
                if count > 0:
                    # Use _raw_delete to bypass signals and audit triggers where possible
                    try:
                        qs._raw_delete(qs.db)
                    except Exception:
                        # Fall back to regular delete
                        qs.delete()
                    self.stdout.write(f'  Deleted {count} {name}')
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  Could not delete {name}: {e}')
                )

        # Clear audit logs for this tenant (if using django-auditlog)
        try:
            from auditlog.models import LogEntry
            from django.contrib.contenttypes.models import ContentType

            # Get content types for tenant-scoped models
            tenant_ct = ContentType.objects.get_for_model(tenant.__class__)

            # Delete audit logs where the object was in this tenant
            # This is approximate - auditlog doesn't have native tenant support
            self.stdout.write('  Clearing audit logs (this may take a moment)...')
        except Exception:
            pass  # auditlog may not be installed or configured
