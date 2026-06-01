"""
Tests for the Digital Work Instructions (DWI) subsystem.

Phase 1 scope (this file initially): model layer for Substep core models.
- Substep
- SubstepCompletion
- SubstepResource
- SubstepTranslation
- Steps.sequencing_mode

Later phases (will be added as they ship):
- Phase 2 — SubstepGateCompletion + SubstepResponse + per-node capture services
- Phase 3 — Substep-aware StepExecutionMeasurement / StepMeasurementRequirement
- Phase 4 — Authoring approval workflow (ProcessStep.approval_status,
  submit_step_for_approval, try_activate_process_version)
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from Tracker.models import (
    Companies,
    EquipmentType,
    Parts,
    PartTypes,
    Processes,
    ProcessStatus,
    ProcessStep,
    SequencingMode,
    StepExecution,
    Steps,
    Substep,
    SubstepCompletion,
    SubstepResource,
    SubstepTranslation,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.utils.tenant_context import (
    reset_current_tenant,
    set_current_tenant_id,
)

User = get_user_model()


class DwiPhase1BaseTestCase(TestCase):
    """Shared setup for Phase 1 model tests."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name="DWI Shop", slug="dwi-shop")
        cls._class_cv_token = set_current_tenant_id(cls.tenant.id)

        cls.user = User.objects.create_user(
            username="dwi_user", email="dwi@test.com",
            password="testpass", tenant=cls.tenant,
        )

        cls.part_type = PartTypes.objects.create(
            name="Spacer", ID_prefix="SPC", tenant=cls.tenant,
        )
        cls.process = Processes.objects.create(
            name="Spacer OD Turn",
            part_type=cls.part_type,
            tenant=cls.tenant,
            status=ProcessStatus.APPROVED,
        )
        cls.step = Steps.objects.create(
            name="OD Turn", part_type=cls.part_type, tenant=cls.tenant,
        )
        ProcessStep.objects.create(process=cls.process, step=cls.step, order=1)

        cls.work_order = WorkOrder.objects.create(
            tenant=cls.tenant,
            ERP_id="WO-DWI-001",
            workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1,
            process=cls.process,
        )
        cls.part = Parts.objects.create(
            tenant=cls.tenant,
            ERP_id="SPC-001",
            part_type=cls.part_type,
            work_order=cls.work_order,
            step=cls.step,
        )
        cls.step_execution = StepExecution.objects.create(
            tenant=cls.tenant,
            part=cls.part,
            step=cls.step,
            visit_number=1,
        )

        cls.equipment_type = EquipmentType.objects.create(
            name="Digital micrometer 0-1 in",
            tenant=cls.tenant,
        )

    @classmethod
    def tearDownClass(cls):
        token = getattr(cls, '_class_cv_token', None)
        if token is not None:
            try:
                reset_current_tenant(token)
            except (LookupError, ValueError):
                pass
        super().tearDownClass()


class SubstepModelTests(DwiPhase1BaseTestCase):
    """Substep creation, ordering, optional and signature flags."""

    def test_create_minimal_substep(self):
        substep = Substep.objects.create(
            tenant=self.tenant,
            step=self.step,
            order=0,
            title="Setup OD offsets",
        )
        self.assertEqual(substep.step, self.step)
        self.assertEqual(substep.order, 0)
        self.assertEqual(substep.title, "Setup OD offsets")
        # Defaults
        self.assertEqual(substep.body_blocks, [])
        self.assertFalse(substep.is_optional)
        self.assertFalse(substep.requires_signature)
        self.assertIsNone(substep.expected_duration)
        self.assertIsNone(substep.sampling_rule_id)
        self.assertIsNone(substep.source_library_substep_id)

    def test_unique_step_order_constraint(self):
        Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0, title="A",
        )
        with self.assertRaises(IntegrityError):
            Substep.objects.create(
                tenant=self.tenant, step=self.step, order=0, title="A duplicate at order 0",
            )

    def test_unique_step_order_constraint_ignores_soft_deleted(self):
        # Constraint is partial (deleted_at IS NULL), so soft-deleting a row
        # frees its (step, order) slot for a new live row.
        from django.utils import timezone
        a = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0, title="A",
        )
        # Soft-delete via direct field update (SecureModel doesn't expose a
        # .void() method on Substep itself; the soft-delete fields are set
        # by callers / management actions in production).
        Substep.unscoped.filter(pk=a.pk).update(
            deleted_at=timezone.now(), archived=True,
        )
        # Should now succeed since `a` has deleted_at set; the partial
        # unique constraint only applies to live rows.
        b = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0, title="A successor",
        )
        self.assertEqual(b.title, "A successor")

    def test_body_blocks_accepts_tiptap_doc(self):
        # Phase 1: model just stores arbitrary JSON. The TipTap shape is
        # enforced by the editor and (later) by server-side validation.
        doc = {"type": "doc", "content": [{"type": "paragraph"}]}
        substep = Substep.objects.create(
            tenant=self.tenant,
            step=self.step,
            order=0,
            title="With body",
            body_blocks=doc,
        )
        substep.refresh_from_db()
        self.assertEqual(substep.body_blocks, doc)

    def test_substeps_ordered_within_step(self):
        for order, title in [(2, "C"), (0, "A"), (1, "B")]:
            Substep.objects.create(
                tenant=self.tenant, step=self.step, order=order, title=title,
            )
        titles = list(self.step.substeps.order_by('order').values_list('title', flat=True))
        self.assertEqual(titles, ["A", "B", "C"])

    def test_str_includes_step_and_order(self):
        substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=3, title="Final inspection",
        )
        s = str(substep)
        self.assertIn("3", s)
        self.assertIn("Final inspection", s)


class StepsSequencingModeTests(DwiPhase1BaseTestCase):
    """Steps.sequencing_mode added by Phase 1 migration."""

    def test_default_is_sequential(self):
        new_step = Steps.objects.create(
            name="Another Step", part_type=self.part_type, tenant=self.tenant,
        )
        self.assertEqual(new_step.sequencing_mode, SequencingMode.SEQUENTIAL)
        self.assertEqual(new_step.sequencing_mode, 'sequential')

    def test_free_order_assignable(self):
        free = Steps.objects.create(
            name="Free Step",
            part_type=self.part_type,
            tenant=self.tenant,
            sequencing_mode=SequencingMode.FREE_ORDER,
        )
        self.assertEqual(free.sequencing_mode, 'free_order')

    def test_existing_steps_picked_up_default(self):
        # self.step was created before any sequencing_mode references in tests;
        # the field's default kicks in for fresh rows.
        self.step.refresh_from_db()
        self.assertEqual(self.step.sequencing_mode, 'sequential')


class SubstepCompletionTests(DwiPhase1BaseTestCase):
    """Operator completion records keyed on (StepExecution, Substep)."""

    def setUp(self):
        super().setUp()
        self.substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0, title="Setup",
        )

    def test_create_completion(self):
        completion = SubstepCompletion.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=self.substep,
            completed_by=self.user,
        )
        self.assertEqual(completion.step_execution, self.step_execution)
        self.assertEqual(completion.substep, self.substep)
        self.assertEqual(completion.completed_by, self.user)
        self.assertIsNotNone(completion.completed_at)
        self.assertFalse(completion.marked_not_applicable)
        # Signature fields default to null/NONE.
        self.assertIsNone(completion.signature_data)
        self.assertEqual(completion.verification_method, 'NONE')

    def test_unique_per_execution_and_substep(self):
        SubstepCompletion.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=self.substep,
            completed_by=self.user,
        )
        with self.assertRaises(IntegrityError):
            SubstepCompletion.objects.create(
                tenant=self.tenant,
                step_execution=self.step_execution,
                substep=self.substep,
                completed_by=self.user,
            )

    def test_n_a_completion_with_notes(self):
        optional_substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=1,
            title="Optional setup variant", is_optional=True,
        )
        completion = SubstepCompletion.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=optional_substep,
            completed_by=self.user,
            marked_not_applicable=True,
            notes="Variant not used on this lot",
        )
        self.assertTrue(completion.marked_not_applicable)
        self.assertEqual(completion.notes, "Variant not used on this lot")

    def test_signature_capture_fields(self):
        signed_substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=2,
            title="Final sign-off", requires_signature=True,
        )
        completion = SubstepCompletion.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=signed_substep,
            completed_by=self.user,
            signature_data="data:image/png;base64,iVBORw0KGgo...",  # truncated for test
            signature_meaning="I confirm the part is ready to release",
            verification_method='PASSWORD',
            ip_address="10.0.0.1",
        )
        self.assertEqual(completion.signature_meaning, "I confirm the part is ready to release")
        self.assertEqual(completion.verification_method, 'PASSWORD')
        self.assertEqual(completion.ip_address, "10.0.0.1")


class SubstepResourceTests(DwiPhase1BaseTestCase):
    """Equipment/material/PPE references attached to a substep."""

    def setUp(self):
        super().setUp()
        self.substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0, title="Measure OD",
        )

    def test_create_resource_with_equipment_type(self):
        resource = SubstepResource.objects.create(
            tenant=self.tenant,
            substep=self.substep,
            equipment_type=self.equipment_type,
            notes="Needs to be in cal",
        )
        self.assertEqual(resource.equipment_type, self.equipment_type)
        self.assertTrue(resource.required)
        self.assertEqual(resource.notes, "Needs to be in cal")

    def test_resource_requires_equipment_type(self):
        # Phase 1 ships with only equipment_type as the resource FK.
        # CheckConstraint enforces it is non-null.
        with self.assertRaises(IntegrityError):
            SubstepResource.objects.create(
                tenant=self.tenant,
                substep=self.substep,
                equipment_type=None,
            )


class SubstepTranslationTests(DwiPhase1BaseTestCase):
    """Localized title + body for a substep."""

    def setUp(self):
        super().setUp()
        self.substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0, title="Setup OD offsets",
        )

    def test_create_translation(self):
        translation = SubstepTranslation.objects.create(
            tenant=self.tenant,
            substep=self.substep,
            language="es-MX",
            title="Ajustar offsets OD",
        )
        self.assertEqual(translation.language, "es-MX")
        self.assertEqual(translation.title, "Ajustar offsets OD")
        self.assertEqual(translation.body_blocks, [])

    def test_unique_per_substep_and_language(self):
        SubstepTranslation.objects.create(
            tenant=self.tenant, substep=self.substep,
            language="es-MX", title="Ajustar offsets OD",
        )
        with self.assertRaises(IntegrityError):
            SubstepTranslation.objects.create(
                tenant=self.tenant, substep=self.substep,
                language="es-MX", title="Conflicting translation",
            )

    def test_multiple_languages_for_same_substep(self):
        SubstepTranslation.objects.create(
            tenant=self.tenant, substep=self.substep, language="es-MX",
            title="Ajustar offsets OD",
        )
        SubstepTranslation.objects.create(
            tenant=self.tenant, substep=self.substep, language="pt-BR",
            title="Configurar offsets de DE",
        )
        self.assertEqual(self.substep.translations.count(), 2)


class SubstepFkOnDeleteTests(DwiPhase1BaseTestCase):
    """Verify FK `on_delete` is configured correctly per the model spec.

    The platform's soft-delete-only philosophy means actual hard-delete
    cascade isn't exercised in production code paths. We only assert the
    field-level on_delete configuration matches the design doc.
    """

    def test_substep_step_fk_cascades(self):
        from django.db import models as dj_models
        field = Substep._meta.get_field('step')
        self.assertEqual(field.remote_field.on_delete, dj_models.CASCADE)

    def test_substep_sampling_rule_fk_set_null(self):
        from django.db import models as dj_models
        field = Substep._meta.get_field('sampling_rule')
        self.assertEqual(field.remote_field.on_delete, dj_models.SET_NULL)

    def test_completion_step_execution_fk_cascades(self):
        from django.db import models as dj_models
        field = SubstepCompletion._meta.get_field('step_execution')
        self.assertEqual(field.remote_field.on_delete, dj_models.CASCADE)

    def test_completion_substep_fk_cascades(self):
        from django.db import models as dj_models
        field = SubstepCompletion._meta.get_field('substep')
        self.assertEqual(field.remote_field.on_delete, dj_models.CASCADE)

    def test_completion_completed_by_fk_protects(self):
        # PROTECT prevents deleting a user who has signed off substeps —
        # preserves the audit trail.
        from django.db import models as dj_models
        field = SubstepCompletion._meta.get_field('completed_by')
        self.assertEqual(field.remote_field.on_delete, dj_models.PROTECT)

    def test_resource_substep_fk_cascades(self):
        from django.db import models as dj_models
        field = SubstepResource._meta.get_field('substep')
        self.assertEqual(field.remote_field.on_delete, dj_models.CASCADE)

    def test_resource_equipment_type_fk_protects(self):
        # PROTECT prevents accidentally deleting an EquipmentType referenced
        # by a substep — engineers would notice when they tried.
        from django.db import models as dj_models
        field = SubstepResource._meta.get_field('equipment_type')
        self.assertEqual(field.remote_field.on_delete, dj_models.PROTECT)

    def test_translation_substep_fk_cascades(self):
        from django.db import models as dj_models
        field = SubstepTranslation._meta.get_field('substep')
        self.assertEqual(field.remote_field.on_delete, dj_models.CASCADE)


class SubstepTenantIsolationTests(TestCase):
    """SecureModel inheritance — substeps are tenant-scoped."""

    def test_substep_filtered_by_tenant(self):
        from Tracker.utils.tenant_context import tenant_context

        tenant_a = Tenant.objects.create(name="A", slug="dwi-a")
        tenant_b = Tenant.objects.create(name="B", slug="dwi-b")

        with tenant_context(tenant_a):
            pt_a = PartTypes.objects.create(name="PT-A", ID_prefix="A", tenant=tenant_a)
            step_a = Steps.objects.create(name="Step A", part_type=pt_a, tenant=tenant_a)
            Substep.objects.create(
                tenant=tenant_a, step=step_a, order=0, title="A's substep",
            )

        with tenant_context(tenant_b):
            pt_b = PartTypes.objects.create(name="PT-B", ID_prefix="B", tenant=tenant_b)
            step_b = Steps.objects.create(name="Step B", part_type=pt_b, tenant=tenant_b)
            Substep.objects.create(
                tenant=tenant_b, step=step_b, order=0, title="B's substep",
            )

        # Each tenant sees only its own
        with tenant_context(tenant_a):
            visible = list(Substep.objects.values_list('title', flat=True))
            self.assertEqual(visible, ["A's substep"])

        with tenant_context(tenant_b):
            visible = list(Substep.objects.values_list('title', flat=True))
            self.assertEqual(visible, ["B's substep"])


class SubstepExpectedDurationTests(DwiPhase1BaseTestCase):
    """`expected_duration` is informational — just verify it round-trips."""

    def test_duration_round_trip(self):
        substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0,
            title="Long substep", expected_duration=timedelta(minutes=12, seconds=30),
        )
        substep.refresh_from_db()
        self.assertEqual(substep.expected_duration, timedelta(minutes=12, seconds=30))
