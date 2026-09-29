"""Deleted configuration stops applying.

DELETE on a SecureModel archives the row, and `.objects` scopes by tenant but does NOT
exclude archived rows — so a reader that forgot `archived=False` kept applying a rule,
a BOM line or a substep someone had deleted. These cover the ones whose effect reaches
the floor: a part sampled by a deleted rule, material demanded by a deleted BOM line,
an operator blocked by a deleted substep, and — for material on hand — a voided lot
counted as stock.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from Tracker.models import (
    BOM, BOMLine, Material, MaterialLot, Orders, OrdersStatus, Parts, PartsStatus,
    PartTypes, Processes, ProcessStep, SamplingRule, SamplingRuleSet, Steps, Substep,
    Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.tests.base import TenantContextMixin
from Tracker.tests.test_dwi import DwiPhase1BaseTestCase

User = get_user_model()


class DeletedSamplingRuleTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Sampling", slug="deleted-sampling")
        self.set_tenant_context(self.tenant)
        self.user = User.objects.create_user(username="s", email="s@x.test", password="x",
                                             tenant=self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget", ID_prefix="W")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.step = Steps.objects.create(tenant=self.tenant, name="Inspect", part_type=self.pt)
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        order = Orders.objects.create(tenant=self.tenant, name="O", customer=self.user,
                                      order_status=OrdersStatus.IN_PROGRESS)
        wo = WorkOrder.objects.create(tenant=self.tenant, ERP_id="WO-S", related_order=order,
                                      workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=5)
        self.ruleset = SamplingRuleSet.objects.create(
            tenant=self.tenant, name="R", part_type=self.pt, process=self.process,
            step=self.step, active=True, is_fallback=False)
        self.rule = SamplingRule.objects.create(
            tenant=self.tenant, ruleset=self.ruleset, rule_type='EVERY_NTH_PART', value=1,
            order=1)
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="WO-S-1", work_order=wo, part_type=self.pt,
            step=self.step, order=order, part_status=PartsStatus.PENDING)

    def _requires_sampling(self):
        from Tracker.services.mes.sampling_applier import SamplingFallbackApplier
        return SamplingFallbackApplier(self.part).evaluate()["requires_sampling"]

    def test_a_deleted_rule_no_longer_samples(self):
        self.assertTrue(self._requires_sampling())
        self.rule.delete()
        self.assertFalse(self._requires_sampling())

    def test_a_deleted_ruleset_no_longer_samples(self):
        self.ruleset.delete()  # archived, but still `active=True`
        self.assertFalse(self._requires_sampling())


class DeletedBomLineAndVoidedLotTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="BOM", slug="deleted-bom")
        self.set_tenant_context(self.tenant)
        self.asm = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        proc = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.asm,
                                        status="APPROVED", is_current_version=True)
        bom = BOM.objects.create(tenant=self.tenant, part_type=self.asm, revision="A",
                                 bom_type="ASSEMBLY", status="RELEASED", is_current_version=True)
        self.seal = Material.objects.create(tenant=self.tenant, name="Seal")
        self.line = BOMLine.objects.create(tenant=self.tenant, bom=bom, material=self.seal,
                                           quantity=Decimal(1), source="BUY", line_number=1)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-B", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=3, process=proc)

    def _rows(self):
        from Tracker.services.mes.requirements import work_order_material_requirements
        return {r['component']: r for r in work_order_material_requirements(self.wo)['rows']}

    def test_a_deleted_bom_line_is_not_demanded(self):
        self.assertIn("Seal", self._rows())
        self.line.delete()
        self.assertNotIn("Seal", self._rows())

    def test_a_voided_lot_is_not_on_hand(self):
        user = User.objects.create_user(username="b", email="b@x.test", password="x",
                                        tenant=self.tenant)
        lot = MaterialLot.objects.create(
            tenant=self.tenant, lot_number="L1", material=self.seal, received_date=date.today(),
            received_by=user, quantity=Decimal(3), quantity_remaining=Decimal(3),
            unit_of_measure="EA", status="ACCEPTED")
        self.assertEqual(self._rows()["Seal"]['short_qty'], 0)
        lot.delete()
        self.assertEqual(self._rows()["Seal"]['short_qty'], 3)


class DeletedSubstepSequencingTests(DwiPhase1BaseTestCase):
    def test_a_deleted_required_substep_does_not_block_the_next(self):
        from Tracker.models import SequencingMode
        from Tracker.services.dwi.operator_capture import _enforce_sequencing
        self.step.sequencing_mode = SequencingMode.SEQUENTIAL
        self.step.save(update_fields=["sequencing_mode"])
        first = Substep.objects.create(tenant=self.tenant, step=self.step, order=0,
                                       title="Torque", is_optional=False)
        second = Substep.objects.create(tenant=self.tenant, step=self.step, order=1,
                                        title="Leak test")
        with self.assertRaises(ValidationError):
            _enforce_sequencing(second, step_execution=self.step_execution)
        first.delete()
        _enforce_sequencing(second, step_execution=self.step_execution)  # no longer blocked


class DeletedRecordTests(TenantContextMixin, TestCase):
    """Records deleted because they were wrong stop counting."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Records", slug="deleted-records")
        self.set_tenant_context(self.tenant)

    def test_a_discarded_draft_schedule_is_not_the_latest_draft(self):
        """Discarding a draft soft-deletes it (queryset `.delete()`), and the draft
        lookup didn't exclude archived rows — so a discarded draft came back."""
        from datetime import timedelta
        from django.utils import timezone
        from Tracker.models.scheduling import ScheduleResult
        from Tracker.services.scheduling.scenario import _latest_draft, discard_draft
        now = timezone.now()
        ScheduleResult.objects.create(tenant=self.tenant, horizon_start=now,
                                      horizon_end=now + timedelta(days=1), is_draft=True)
        self.assertIsNotNone(_latest_draft(self.tenant))
        discard_draft(self.tenant)
        self.assertIsNone(_latest_draft(self.tenant))

    def test_a_deleted_part_approval_no_longer_approves(self):
        from Tracker.models import Companies, PartApproval
        from Tracker.services.qms.part_approval import approving_record_for
        pt = PartTypes.objects.create(tenant=self.tenant, name="Bracket")
        supplier = Companies.objects.create(tenant=self.tenant, name="Acme Machining")
        approval = PartApproval.objects.create(tenant=self.tenant, part_type=pt,
                                               supplier=supplier, status="APPROVED")
        self.assertEqual(approving_record_for(part_type=pt, supplier=supplier), approval)
        approval.delete()
        self.assertIsNone(approving_record_for(part_type=pt, supplier=supplier))
