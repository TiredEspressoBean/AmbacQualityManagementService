"""Every link to a versioned model has a declared policy, and the policies are carried out.

See Tracker/services/core/version_links.py. The guard is the point: before it, a new FK
to a versioned model silently stayed on the old version when that model versioned.
"""
from datetime import date

from django.apps import apps
from django.contrib.contenttypes.fields import GenericRelation
from django.test import SimpleTestCase, TestCase

from Tracker.services.core.version_links import LINKS, POLICIES
from Tracker.tests.base import TenantContextMixin


def _links_to_versioned_models():
    """"<Owner>.<field>" for every FK / O2O / M2M whose target is a versioned model."""
    versioned = {m for m in apps.get_models() if getattr(m, '_is_versioned', False)}
    found = set()
    for m in apps.get_models():
        for f in m._meta.get_fields():
            if not getattr(f, 'is_relation', False) or isinstance(f, GenericRelation):
                continue
            if not getattr(f, 'concrete', False) and not f.many_to_many:
                continue  # reverse accessors
            if f.many_to_many and f.auto_created:
                continue
            if f.related_model in versioned and f.name != 'previous_version':
                found.add(f"{m.__name__}.{f.name}")
    return found


class VersionLinkRegistryTests(SimpleTestCase):
    def test_every_link_to_a_versioned_model_has_a_policy(self):
        missing = sorted(_links_to_versioned_models() - set(LINKS))
        self.assertFalse(missing, (
            "These links point at a versioned model but have no version policy. When "
            "the target versions, should each FOLLOW it (same thing, updated), STAY on "
            "history, be COPIED, or is it the MODEL's / change control's (MANAGED) job? "
            "Add them to Tracker/services/core/version_links.py LINKS:\n  "
            + "\n  ".join(missing)))

    def test_no_stale_or_invalid_entries(self):
        stale = sorted(set(LINKS) - _links_to_versioned_models())
        self.assertFalse(stale, f"LINKS names links that don't exist: {stale}")
        bad = {k: v for k, v in LINKS.items() if v not in POLICIES}
        self.assertFalse(bad, bad)


class VersionLinkBehaviourTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        from Tracker.models import Tenant
        self.tenant = Tenant.objects.create(name="Links", slug="version-links")
        self.set_tenant_context(self.tenant)

    def test_a_machine_edit_keeps_its_calibration_and_downtime(self):
        """A machine's calibrations stayed on the old version, so the CURRENT machine
        read as uncalibrated (and not operational — the scheduler dropped it)."""
        from django.utils import timezone
        from datetime import timedelta
        from Tracker.models import CalibrationRecord, DowntimeEvent, Equipments, EquipmentType
        et = EquipmentType.objects.create(tenant=self.tenant, name="CMM",
                                          requires_calibration=True)
        mill = Equipments.objects.create(tenant=self.tenant, name="Mill 3", equipment_type=et)
        CalibrationRecord.objects.create(
            tenant=self.tenant, equipment=mill, calibration_date=date.today(),
            due_date=date.today() + timedelta(days=365), result='pass')
        now = timezone.now()
        from django.contrib.auth import get_user_model
        reporter = get_user_model().objects.create_user(
            username="dt-reporter", email="dt@c.test", password="x", tenant=self.tenant)
        DowntimeEvent.objects.create(tenant=self.tenant, equipment=mill, reported_by=reporter,
                                     start_time=now + timedelta(days=2),
                                     end_time=now + timedelta(days=3))
        new = mill.create_new_version(user=None, change_description="Renamed",
                                      name="Mill 3 (Haas)")
        self.assertEqual(new.calibration_records.count(), 1)
        self.assertEqual(new.calibration_status, 'CURRENT')
        self.assertEqual(DowntimeEvent.objects.filter(equipment=new).count(), 1)

    def test_a_supplier_edit_keeps_its_approvals(self):
        """A supplier's part approvals stayed on the old version, so a renamed supplier
        was suddenly unapproved for every part."""
        from Tracker.models import Companies, PartApproval, PartTypes
        from Tracker.services.qms.part_approval import approving_record_for
        pt = PartTypes.objects.create(tenant=self.tenant, name="Bracket")
        acme = Companies.objects.create(tenant=self.tenant, name="Acme")
        PartApproval.objects.create(tenant=self.tenant, part_type=pt, supplier=acme,
                                    status="APPROVED")
        new = acme.create_new_version(user=None, change_description="Renamed",
                                      name="Acme Machining")
        self.assertIsNotNone(approving_record_for(part_type=pt, supplier=new))

    def test_a_part_type_edit_keeps_its_process_and_bom(self):
        from Tracker.models import BOM, PartTypes, Processes
        pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        proc = Processes.objects.create(tenant=self.tenant, name="Build", part_type=pt,
                                        status="APPROVED")
        bom = BOM.objects.create(tenant=self.tenant, part_type=pt, revision="A",
                                 bom_type="ASSEMBLY", status="RELEASED")
        new = pt.create_new_version(user=None, change_description="Renamed",
                                    name="Injector Mk2")
        proc.refresh_from_db()
        bom.refresh_from_db()
        self.assertEqual(proc.part_type_id, new.id)
        self.assertEqual(bom.part_type_id, new.id)

    def test_a_step_version_copies_its_machine_eligibility(self):
        """A step version belongs to a draft process revision; the old step stays in
        force, so its eligibility is COPIED — the old step keeps its machines, and the
        new step has them too (it had none, so the revision had no eligible machine)."""
        from Tracker.models import Equipments, PartTypes, Processes, ProcessStep, Steps
        from Tracker.models.scheduling import StepEquipmentAffinity
        pt = PartTypes.objects.create(tenant=self.tenant, name="Pump")
        proc = Processes.objects.create(tenant=self.tenant, name="P", part_type=pt,
                                        status="APPROVED")
        step = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Drill")
        ProcessStep.objects.create(process=proc, step=step, order=1)
        mill = Equipments.objects.create(tenant=self.tenant, name="Mill 1")
        StepEquipmentAffinity.objects.create(tenant=self.tenant, step=step, equipment=mill,
                                             affinity="preferred")
        new = step.create_new_version(user=None, change_description="Revise")
        self.assertTrue(StepEquipmentAffinity.objects.filter(step=step, equipment=mill).exists())
        self.assertTrue(StepEquipmentAffinity.objects.filter(step=new, equipment=mill).exists())

    def test_a_repair_code_edit_keeps_its_place_in_rebuild_presets(self):
        from Tracker.models import PartTypes
        from Tracker.models.reman import RebuildScopePreset, RepairCode
        core_type = PartTypes.objects.create(tenant=self.tenant, name="Core")
        code = RepairCode.objects.create(tenant=self.tenant, code="NZL", name="Nozzle")
        preset = RebuildScopePreset.objects.create(tenant=self.tenant, name="Standard",
                                                   core_type=core_type)
        preset.codes.add(code)
        new = code.create_new_version(user=None, change_description="Renamed",
                                      name="Nozzle recondition")
        preset.refresh_from_db()
        self.assertEqual(list(preset.codes.values_list("id", flat=True)), [new.id])
