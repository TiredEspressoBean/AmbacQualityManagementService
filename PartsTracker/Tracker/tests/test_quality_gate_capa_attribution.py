"""A quality-gate-raised CAPA is System-initiated and lands in a real queue.

Two bugs in `_raise_capa_or_scar`, both stemming from it treating the
incidental request user as the CAPA's initiator:

1. **Mis-attribution.** The gate is machine-triggered — it fires because a
   metric crossed a threshold. The `user` in scope is merely whoever saved
   the record that tripped it, often an operator who does not hold
   `initiate_capa`. Setting `initiated_by=<that operator>` produced an audit
   trail claiming an unauthorized user initiated a governance record, and
   (via `verify_capa_effectiveness`'s `user == capa.initiated_by` check)
   silently marked them ineligible to verify unrelated work.

2. **Silent CAPA.** The gate set no assignee. `notify_assignment` returns
   early without `assigned_to_id`, so nothing emitted `capa.assigned`. The
   only other path, `trigger_approval_for_critical_capa`, fires solely for
   MAJOR/CRITICAL and only when the tenant has a current CAPA_APPROVAL
   template. A MINOR gate could create a CAPA and tell nobody.

Note this is attribution, not authorization: the gate must fire regardless
of who tripped it. Permission-checking here would let an operator's missing
`initiate_capa` suppress a quality gate — strictly worse than a
mis-attributed record.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model

from Tracker.models import (
    CAPA, Companies, PartTypes, Processes, ProcessStep, SamplingRuleSet,
    Steps, Tenant, TenantGroup, UserRole,
)
from Tracker.services.qms.quality_gate import _default_capa_owner, _raise_capa_or_scar
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class _FakeFiring:
    """Stand-in for StepGateFiring — _raise_capa_or_scar only reads these."""
    def __init__(self, metric_value, threshold, report=None):
        self.metric_value = metric_value
        self.threshold = threshold
        self.triggered_by_report = report


class QualityGateCapaAttributionTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Gate Attr", slug="gate-attr", tier="PRO",
        )
        self.set_tenant_context(self.tenant)
        User = get_user_model()

        # Tenant creation seeds the preset groups (GroupSeeder via signal), so
        # look them up rather than creating duplicates.
        def group(name):
            return TenantGroup.objects.get(tenant=self.tenant, name=name)

        # The operator who trips the gate — deliberately NOT a QA role and
        # with no initiate_capa. Pre-fix this user became initiated_by.
        self.operator = User.objects.create_user(
            username="ga-op", email="ga-op@test.test", password="x",
            tenant=self.tenant,
        )
        UserRole.objects.create(user=self.operator, group=group('Operator'))

        self.qa_manager = User.objects.create_user(
            username="ga-qam", email="ga-qam@test.test", password="x",
            tenant=self.tenant,
        )
        UserRole.objects.create(user=self.qa_manager, group=group('QA Manager'))

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P-GA", part_type=self.pt,
        )
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Gate Step",
            step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.supplier = Companies.objects.create(
            tenant=self.tenant, name="Acme Supply", description="Gate test supplier",
        )

    def _ruleset(self, capa_type="", severity=""):
        return SamplingRuleSet.objects.create(
            tenant=self.tenant, name="RS-Gate", step=self.step,
            part_type=self.pt,
            gate_metric='FAIL_RATE_PCT', gate_threshold=Decimal('10.000'),
            gate_actions=['RAISE_CAPA_SCAR'],
            gate_capa_type=capa_type, gate_capa_severity=severity,
        )

    # -- attribution --------------------------------------------------------

    def test_gate_capa_is_system_initiated_not_the_tripping_user(self):
        """The core fix: the operator who tripped the gate must NOT become
        the initiator of record."""
        rs = self._ruleset()
        firing = _FakeFiring(Decimal('25.000'), Decimal('10.000'))
        capa = _raise_capa_or_scar(
            rs, firing, material_lot=None, user=self.operator,
        )
        self.assertIsNone(
            capa.initiated_by,
            'a machine-raised CAPA must be System-initiated, not attributed '
            'to whoever happened to trip the gate',
        )
        self.assertNotEqual(capa.initiated_by_id, self.operator.id)

    def test_gate_scar_is_system_initiated(self):
        rs = self._ruleset(capa_type='SUPPLIER')
        rs.supplier = self.supplier
        rs.save(update_fields=['supplier'])
        firing = _FakeFiring(Decimal('30.000'), Decimal('10.000'))
        capa = _raise_capa_or_scar(
            rs, firing, material_lot=None, user=self.operator,
        )
        self.assertEqual(capa.capa_type, 'SUPPLIER')
        self.assertIsNone(capa.initiated_by)

    def test_problem_statement_records_the_gate_and_the_numbers(self):
        """With no initiator, the record itself has to say where it came
        from — otherwise a System CAPA is unexplainable."""
        rs = self._ruleset()
        firing = _FakeFiring(Decimal('25.000'), Decimal('10.000'))
        capa = _raise_capa_or_scar(
            rs, firing, material_lot=None, user=self.operator,
        )
        self.assertIn('Auto-raised by quality gate', capa.problem_statement)
        self.assertIn('RS-Gate', capa.problem_statement)
        self.assertIn('Gate Step', capa.problem_statement)
        self.assertIn('25.000', capa.problem_statement)
        self.assertIn('10.000', capa.problem_statement)

    # -- not silent ---------------------------------------------------------

    def test_gate_capa_is_assigned_so_it_notifies(self):
        """notify_assignment returns early without assigned_to_id, so an
        unassigned gate CAPA would emit nothing at all."""
        rs = self._ruleset()
        firing = _FakeFiring(Decimal('25.000'), Decimal('10.000'))
        capa = _raise_capa_or_scar(
            rs, firing, material_lot=None, user=self.operator,
        )
        self.assertEqual(capa.assigned_to_id, self.qa_manager.id,
                         'gate CAPA should land with the QA Manager')

    def test_gate_scar_is_assigned(self):
        rs = self._ruleset(capa_type='SUPPLIER')
        rs.supplier = self.supplier
        rs.save(update_fields=['supplier'])
        firing = _FakeFiring(Decimal('30.000'), Decimal('10.000'))
        capa = _raise_capa_or_scar(
            rs, firing, material_lot=None, user=self.operator,
        )
        self.assertEqual(capa.assigned_to_id, self.qa_manager.id)

    def test_owner_lookup_prefers_qa_manager_over_inspector(self):
        User = get_user_model()
        inspector = User.objects.create_user(
            username="ga-qai", email="ga-qai@test.test", password="x",
            tenant=self.tenant,
        )
        UserRole.objects.create(
            user=inspector,
            group=TenantGroup.objects.get(tenant=self.tenant, name='QA Inspector'),
        )
        self.assertEqual(_default_capa_owner(self.tenant).id, self.qa_manager.id)

    def test_owner_lookup_falls_back_to_inspector(self):
        UserRole.objects.filter(user=self.qa_manager).delete()
        User = get_user_model()
        inspector = User.objects.create_user(
            username="ga-qai2", email="ga-qai2@test.test", password="x",
            tenant=self.tenant,
        )
        UserRole.objects.create(
            user=inspector,
            group=TenantGroup.objects.get(tenant=self.tenant, name='QA Inspector'),
        )
        self.assertEqual(_default_capa_owner(self.tenant).id, inspector.id)

    def test_gate_still_fires_with_no_qa_staff(self):
        """Staffing must not break the gate — an unassigned CAPA beats no
        CAPA."""
        UserRole.objects.filter(user=self.qa_manager).delete()
        self.assertIsNone(_default_capa_owner(self.tenant))
        rs = self._ruleset()
        firing = _FakeFiring(Decimal('25.000'), Decimal('10.000'))
        capa = _raise_capa_or_scar(
            rs, firing, material_lot=None, user=self.operator,
        )
        self.assertIsNotNone(capa.pk)
        self.assertIsNone(capa.assigned_to_id)

    def test_owner_lookup_is_tenant_scoped(self):
        """A QA Manager in another tenant must never own this tenant's CAPA."""
        other = Tenant.objects.create(name="Other", slug="ga-other", tier="PRO")
        self.assertEqual(_default_capa_owner(self.tenant).id, self.qa_manager.id)
        self.assertIsNone(_default_capa_owner(other))

    # -- regression: explicit human path keeps attribution ------------------

    def test_explicit_open_scar_still_attributes_to_the_user(self):
        """open_scar is shared with the raise_scar endpoint, which IS an
        explicit human act by someone holding initiate_capa. That path must
        keep recording the initiator."""
        from Tracker.services.qms.scar import open_scar
        capa = open_scar(
            supplier=self.supplier,
            problem_statement='Manually raised against supplier',
            user=self.qa_manager,
        )
        self.assertEqual(capa.initiated_by_id, self.qa_manager.id)
        self.assertIsNone(capa.assigned_to_id,
                          'explicit path leaves assignment to the caller')
        self.assertEqual(CAPA.objects.filter(pk=capa.pk).count(), 1)
