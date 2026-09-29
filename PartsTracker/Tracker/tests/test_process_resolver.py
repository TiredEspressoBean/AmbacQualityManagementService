"""The routing that builds a part type is the APPROVED one, even while a revision is open.

Opening a draft revision makes the approved process non-current (the draft is the new
latest version), but it is still the routing in force until the draft is approved —
approval archives its predecessor. The resolver required `is_current_version`, so during
any open revision BOM explosion, order lines and capable-to-promise all found "no
approved build process".
"""
from django.test import TestCase

from Tracker.models import PartTypes, Processes, Tenant
from Tracker.models.mes_lite import ProcessStatus
from Tracker.services.mes.bom_explosion import _build_process
from Tracker.services.mes.processes import approve_process, create_new_process_version
from Tracker.tests.base import TenantContextMixin


class ProcessResolverTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Resolver", slug="process-resolver")
        self.set_tenant_context(self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Nozzle")
        self.v1 = Processes.objects.create(tenant=self.tenant, name="Nozzle build",
                                           part_type=self.pt, status=ProcessStatus.APPROVED)

    def test_the_approved_process_is_found(self):
        self.assertEqual(_build_process(self.pt), (self.v1, None))

    def test_an_open_revision_does_not_hide_the_approved_process(self):
        draft = create_new_process_version(self.v1, user=None, change_description="Tweak")
        self.v1.refresh_from_db()
        self.assertFalse(self.v1.is_current_version)  # the draft is the latest version
        self.assertEqual(draft.status, ProcessStatus.DRAFT)
        self.assertEqual(_build_process(self.pt), (self.v1, None))

    def test_once_the_revision_is_approved_it_is_the_routing(self):
        from Tracker.models import ProcessStep, Steps
        # A process can't be approved without steps; the revision copies v1's.
        step = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Bore")
        ProcessStep.objects.create(process=self.v1, step=step, order=1)
        draft = create_new_process_version(self.v1, user=None, change_description="Tweak")
        approve_process(draft)
        self.assertEqual(_build_process(self.pt), (draft, None))

    def test_two_different_approved_processes_are_still_ambiguous(self):
        Processes.objects.create(tenant=self.tenant, name="Nozzle alt build",
                                 part_type=self.pt, status=ProcessStatus.APPROVED)
        proc, reason = _build_process(self.pt)
        self.assertIsNone(proc)
        self.assertIn("several", reason)

    def test_capable_to_promise_quotes_against_the_approved_process_during_a_revision(self):
        """A real one-step routing (60 min/piece, one operator on a day shift — the
        test_planning_rccp fixture) so the answer is a quote, not just 'not refused'."""
        from datetime import time as dtime, timedelta
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from Tracker.models import Equipments, ProcessStep, Shift, Steps, StepTiming, WorkCenter
        from Tracker.services.planning import rccp

        shift = Shift.objects.create(
            tenant=self.tenant, code="DAY", name="Day", start_time=dtime(8, 0),
            end_time=dtime(16, 0), days_of_week="0,1,2,3,4", is_active=True)
        operator = get_user_model().objects.create_user(
            username="ctp-op", email="ctp@c.test", password="x", tenant=self.tenant)
        operator.default_shift = shift
        operator.save(update_fields=["default_shift"])
        wc = WorkCenter.objects.create(tenant=self.tenant, name="Cell A", code="A")
        wc.equipment.add(Equipments.objects.create(
            tenant=self.tenant, name="M-1", is_schedulable=True, runs_unattended=False))
        step = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Cut",
                                    step_type="TASK", work_center=wc)
        StepTiming.objects.create(tenant=self.tenant, step=step, cycle_time_minutes=60)
        ProcessStep.objects.create(process=self.v1, step=step, order=1)

        create_new_process_version(self.v1, user=None, change_description="Tweak")
        today = timezone.now().date()
        r = rccp.capable_to_promise(self.tenant, self.pt.id, 5, today + timedelta(days=20),
                                    months=6)
        self.assertTrue(r["feasible"], r)
        self.assertAlmostEqual(r["work_content_hours"]["labor"], 5.0, places=1)
