"""
Seed baseline scheduling data (Phase 0) from existing MES config.

Idempotent. For each tenant (or one named via --tenant):
  * ensure an OptimizationConfig,
  * give every step a StepTiming (cycle time derived from `expected_duration`
    when set, else left at 0 for the planner to fill),
  * add an ELIGIBLE StepEquipmentAffinity for each step's default/backup equipment.

This does not invent machine/changeover data beyond what the MES already knows;
richer timing (setup, load/unload, changeover matrices) is planner-entered.

    python manage.py seed_scheduling [--tenant <slug>]
"""
from django.core.management.base import BaseCommand

from Tracker.models import (
    Equipments,
    OptimizationConfig,
    StepEquipmentAffinity,
    Steps,
    StepTiming,
    Tenant,
)
from Tracker.utils.tenant_context import tenant_context


class Command(BaseCommand):
    help = "Seed baseline scheduling data (StepTiming, affinities, OptimizationConfig)."

    def add_arguments(self, parser):
        parser.add_argument('--tenant', help="Only seed the tenant with this slug.")

    def handle(self, *args, **options):
        tenants = Tenant.objects.all()
        if options.get('tenant'):
            tenants = tenants.filter(slug=options['tenant'])
        if not tenants:
            self.stdout.write(self.style.WARNING("No matching tenants."))
            return

        for tenant in tenants:
            with tenant_context(str(tenant.id)):
                self._seed_tenant(tenant)

    def _seed_tenant(self, tenant):
        _, cfg_created = OptimizationConfig.objects.get_or_create(tenant=tenant)

        timings = affinities = 0
        for step in Steps.objects.filter(is_current_version=True):
            cycle = 0.0
            if step.expected_duration is not None:
                cycle = step.expected_duration.total_seconds() / 60.0
            _, made = StepTiming.objects.get_or_create(
                tenant=tenant, step=step,
                defaults={'cycle_time_minutes': cycle},
            )
            timings += int(made)

            for equip in self._step_equipment(step):
                _, made = StepEquipmentAffinity.objects.get_or_create(
                    tenant=tenant, step=step, equipment=equip,
                    defaults={'affinity': StepEquipmentAffinity.Affinity.ELIGIBLE},
                )
                affinities += int(made)

        self.stdout.write(self.style.SUCCESS(
            f"{tenant.slug}: config {'created' if cfg_created else 'exists'}, "
            f"+{timings} timings, +{affinities} affinities."
        ))

    @staticmethod
    def _step_equipment(step):
        """The step's configured machines (default + backup), de-duplicated."""
        seen = {}
        for equip in (getattr(step, 'default_equipment', None), getattr(step, 'backup_equipment', None)):
            if isinstance(equip, Equipments) and equip.pk not in seen:
                seen[equip.pk] = equip
        return list(seen.values())
