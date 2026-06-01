"""
Tests for the Digital Work Instructions (DWI) subsystem.

Phase 1 — substep core models:
- Substep
- SubstepCompletion
- SubstepResource
- SubstepTranslation
- Steps.sequencing_mode

Phase 2 — per-node operator state:
- SubstepGateCompletion (inline attestation / signature gates)
- SubstepResponse (text / choice / photo / video / scan / file / timer / computed)
- SubstepResponseKind enum

Later phases:
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
    SubstepGateCompletion,
    SubstepResource,
    SubstepResponse,
    SubstepResponseKind,
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


# =============================================================================
# Phase 2 — per-node operator state
# =============================================================================


class DwiPhase2BaseTestCase(DwiPhase1BaseTestCase):
    """Shared setup for Phase 2 tests — adds a substep ready for gate /
    response captures."""

    def setUp(self):
        super().setUp()
        self.substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0, title="Run first piece",
        )


class SubstepResponseKindTests(DwiPhase2BaseTestCase):
    """The discriminator enum covers every non-numeric capture node type."""

    def test_enum_has_expected_values(self):
        # Keep in sync with CAPTURE_NODE_TYPES in
        # ambac-tracker-ui/src/lib/dwi/node-id.ts and the SubstepResponse
        # type union in src/types/dwi.ts. Numeric measurements
        # (MeasurementInput) route through StepExecutionMeasurement, not
        # SubstepResponse, so they're absent here.
        values = {choice[0] for choice in SubstepResponseKind.choices}
        self.assertSetEqual(
            values,
            {'text', 'choice', 'photo', 'video', 'scan', 'file', 'timer', 'computed'},
        )


class SubstepGateCompletionTests(DwiPhase2BaseTestCase):
    """Per-node attestation / signature gate records."""

    def test_create_confirm_gate(self):
        # For kind='confirm' gates the row just records that the checkbox
        # was ticked; signature fields stay null.
        gate = SubstepGateCompletion.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=self.substep,
            node_id="01984a3f-2b1c-7000-8000-000000000001",
            completed_by=self.user,
        )
        self.assertIsNotNone(gate.completed_at)
        self.assertIsNone(gate.signature_data)
        self.assertEqual(gate.verification_method, 'NONE')

    def test_create_signature_gate(self):
        gate = SubstepGateCompletion.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=self.substep,
            node_id="01984a3f-2b1c-7000-8000-000000000002",
            completed_by=self.user,
            signature_data="data:image/png;base64,iVBORw0KGgo...",
            signature_meaning="I verified the tool offset before continuing",
            verification_method='PASSWORD',
            ip_address="10.0.0.1",
        )
        self.assertEqual(gate.verification_method, 'PASSWORD')
        self.assertEqual(gate.signature_meaning, "I verified the tool offset before continuing")
        self.assertEqual(gate.ip_address, "10.0.0.1")

    def test_unique_per_execution_substep_node(self):
        SubstepGateCompletion.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=self.substep,
            node_id="01984a3f-2b1c-7000-8000-000000000003",
            completed_by=self.user,
        )
        with self.assertRaises(IntegrityError):
            SubstepGateCompletion.objects.create(
                tenant=self.tenant,
                step_execution=self.step_execution,
                substep=self.substep,
                node_id="01984a3f-2b1c-7000-8000-000000000003",
                completed_by=self.user,
            )

    def test_different_node_ids_coexist(self):
        # A single substep can have multiple gate nodes; each gets its own row.
        SubstepGateCompletion.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=self.substep,
            node_id="01984a3f-2b1c-7000-8000-000000000004",
            completed_by=self.user,
        )
        SubstepGateCompletion.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=self.substep,
            node_id="01984a3f-2b1c-7000-8000-000000000005",
            completed_by=self.user,
        )
        self.assertEqual(
            SubstepGateCompletion.objects.filter(step_execution=self.step_execution).count(),
            2,
        )


class SubstepResponseTests(DwiPhase2BaseTestCase):
    """Per-node capture rows for text / choice / file / timer / computed."""

    def test_create_text_response(self):
        resp = SubstepResponse.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=self.substep,
            node_id="01984a3f-2b1c-7000-8000-000000000010",
            kind=SubstepResponseKind.TEXT,
            value_text="LOT-2026-04421",
            responded_by=self.user,
        )
        self.assertEqual(resp.kind, 'text')
        self.assertEqual(resp.value_text, "LOT-2026-04421")
        self.assertIsNone(resp.value_document_id)
        self.assertIsNone(resp.value_json)

    def test_create_choice_response(self):
        resp = SubstepResponse.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=self.substep,
            node_id="01984a3f-2b1c-7000-8000-000000000011",
            kind=SubstepResponseKind.CHOICE,
            value_text="Light surface scale",
            responded_by=self.user,
        )
        self.assertEqual(resp.kind, 'choice')

    def test_create_scan_response(self):
        resp = SubstepResponse.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=self.substep,
            node_id="01984a3f-2b1c-7000-8000-000000000012",
            kind=SubstepResponseKind.SCAN,
            value_text="123456789012",  # barcode
            responded_by=self.user,
        )
        self.assertEqual(resp.kind, 'scan')

    def test_create_timer_response_with_json(self):
        timer_payload = {
            "started_at": "2026-05-31T15:00:00Z",
            "completed_at": "2026-05-31T15:00:30Z",
            "elapsed_seconds": 30.0,
            "direction": "countdown",
        }
        resp = SubstepResponse.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=self.substep,
            node_id="01984a3f-2b1c-7000-8000-000000000013",
            kind=SubstepResponseKind.TIMER,
            value_json=timer_payload,
            responded_by=self.user,
        )
        resp.refresh_from_db()
        self.assertEqual(resp.value_json, timer_payload)
        self.assertEqual(resp.value_text, "")  # default for unused field

    def test_create_computed_response_with_json(self):
        computed_payload = {
            "inputs": {"X": "0.002", "Y": "0.001"},
            "result": 0.004472135954999579,
            "in_spec": True,
        }
        resp = SubstepResponse.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=self.substep,
            node_id="01984a3f-2b1c-7000-8000-000000000014",
            kind=SubstepResponseKind.COMPUTED,
            value_json=computed_payload,
            responded_by=self.user,
        )
        resp.refresh_from_db()
        self.assertEqual(resp.value_json["in_spec"], True)
        self.assertEqual(resp.value_json["inputs"]["X"], "0.002")

    def test_unique_per_execution_substep_node(self):
        SubstepResponse.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            substep=self.substep,
            node_id="01984a3f-2b1c-7000-8000-000000000015",
            kind=SubstepResponseKind.TEXT,
            value_text="first",
            responded_by=self.user,
        )
        with self.assertRaises(IntegrityError):
            SubstepResponse.objects.create(
                tenant=self.tenant,
                step_execution=self.step_execution,
                substep=self.substep,
                node_id="01984a3f-2b1c-7000-8000-000000000015",
                kind=SubstepResponseKind.TEXT,
                value_text="conflicting second write",
                responded_by=self.user,
            )

    def test_different_node_ids_coexist_in_same_substep(self):
        # A substep with multiple capture nodes gets multiple response rows.
        for i in range(3):
            SubstepResponse.objects.create(
                tenant=self.tenant,
                step_execution=self.step_execution,
                substep=self.substep,
                node_id=f"01984a3f-2b1c-7000-8000-00000000010{i}",
                kind=SubstepResponseKind.TEXT,
                value_text=f"capture-{i}",
                responded_by=self.user,
            )
        self.assertEqual(
            SubstepResponse.objects.filter(step_execution=self.step_execution).count(),
            3,
        )


class SubstepPhase2FkOnDeleteTests(DwiPhase2BaseTestCase):
    """Verify FK on_delete is configured correctly on Phase 2 models."""

    def test_gate_step_execution_fk_cascades(self):
        from django.db import models as dj_models
        field = SubstepGateCompletion._meta.get_field('step_execution')
        self.assertEqual(field.remote_field.on_delete, dj_models.CASCADE)

    def test_gate_substep_fk_cascades(self):
        from django.db import models as dj_models
        field = SubstepGateCompletion._meta.get_field('substep')
        self.assertEqual(field.remote_field.on_delete, dj_models.CASCADE)

    def test_gate_completed_by_protects(self):
        # PROTECT preserves the audit trail — a user who signed gates
        # can't be hard-deleted without first reassigning / voiding.
        from django.db import models as dj_models
        field = SubstepGateCompletion._meta.get_field('completed_by')
        self.assertEqual(field.remote_field.on_delete, dj_models.PROTECT)

    def test_response_step_execution_fk_cascades(self):
        from django.db import models as dj_models
        field = SubstepResponse._meta.get_field('step_execution')
        self.assertEqual(field.remote_field.on_delete, dj_models.CASCADE)

    def test_response_substep_fk_cascades(self):
        from django.db import models as dj_models
        field = SubstepResponse._meta.get_field('substep')
        self.assertEqual(field.remote_field.on_delete, dj_models.CASCADE)

    def test_response_responded_by_protects(self):
        from django.db import models as dj_models
        field = SubstepResponse._meta.get_field('responded_by')
        self.assertEqual(field.remote_field.on_delete, dj_models.PROTECT)

    def test_response_value_document_set_null(self):
        # If a Documents row is hard-deleted, the response row keeps its
        # other fields and just loses the FK link.
        from django.db import models as dj_models
        field = SubstepResponse._meta.get_field('value_document')
        self.assertEqual(field.remote_field.on_delete, dj_models.SET_NULL)


# =============================================================================
# Phase 3 — substep-aware measurements + two-tier capture pipeline
# =============================================================================
#
# Per architectural decision #21 in DIGITAL_WORK_INSTRUCTIONS_DESIGN.md:
# - DWI MeasurementInput captures always write StepExecutionMeasurement (Tier 1).
# - When the parent substep has is_inspection_point=True, the capture also
#   creates QualityReports + MeasurementResult (Tier 2), which fires
#   record_quality_report_side_effects (auto-quarantine, ncr.opened, sampling).


class DwiPhase3BaseTestCase(DwiPhase1BaseTestCase):
    """Shared setup: a routine substep + an inspection-point substep + a
    numeric MeasurementDefinition with tolerances."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from Tracker.models import MeasurementDefinition

        # Re-set the tenant context — setUpTestData ran the parent's
        # setUpTestData but classroom-level setup may have been torn down.
        cls.measurement_def = MeasurementDefinition.objects.create(
            tenant=cls.tenant,
            label="Outer Diameter",
            type="NUMERIC",
            unit="in",
            nominal=1.247,
            upper_tol=0.002,
            lower_tol=0.002,
            step=cls.step,
        )

    def setUp(self):
        super().setUp()
        self.routine_substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0,
            title="Setup", is_inspection_point=False,
        )
        self.inspection_substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=1,
            title="First piece inspection", is_inspection_point=True,
        )


class SubstepInspectionPointFieldTests(DwiPhase1BaseTestCase):
    """Phase 3 adds the load-bearing flag on Substep."""

    def test_default_is_false(self):
        substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0, title="Routine",
        )
        self.assertFalse(substep.is_inspection_point)

    def test_assignable_at_create(self):
        substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0,
            title="FAI", is_inspection_point=True,
        )
        self.assertTrue(substep.is_inspection_point)


class StepExecutionMeasurementSubstepFkTests(DwiPhase3BaseTestCase):
    """`substep` FK is nullable — null means "Op-level capture, no substep."""

    def test_substep_fk_nullable_default(self):
        from Tracker.models import StepExecutionMeasurement
        sem = StepExecutionMeasurement.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            measurement_definition=self.measurement_def,
            value=1.247,
            recorded_by=self.user,
        )
        self.assertIsNone(sem.substep)

    def test_substep_fk_assignable(self):
        from Tracker.models import StepExecutionMeasurement
        sem = StepExecutionMeasurement.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            measurement_definition=self.measurement_def,
            value=1.247,
            recorded_by=self.user,
            substep=self.routine_substep,
        )
        self.assertEqual(sem.substep, self.routine_substep)

    def test_substep_fk_set_null_on_substep_delete(self):
        from django.db import models as dj_models
        from Tracker.models import StepExecutionMeasurement
        field = StepExecutionMeasurement._meta.get_field('substep')
        self.assertEqual(field.remote_field.on_delete, dj_models.SET_NULL)


class RecordDwiMeasurementTier1Tests(DwiPhase3BaseTestCase):
    """Routine (non-inspection) substep captures stay process-data-only."""

    def test_writes_step_execution_measurement(self):
        from Tracker.models import QualityReports, StepExecutionMeasurement
        from Tracker.services.qms.inline_capture import record_dwi_measurement

        sem = record_dwi_measurement(
            step_execution=self.step_execution,
            substep=self.routine_substep,
            measurement_definition=self.measurement_def,
            value=1.247,
            recorded_by=self.user,
        )
        self.assertIsInstance(sem, StepExecutionMeasurement)
        self.assertEqual(sem.value, 1.247)
        self.assertEqual(sem.substep, self.routine_substep)
        # In-spec value auto-evaluated.
        self.assertTrue(sem.is_within_spec)

        # No QualityReports row created for routine captures.
        self.assertEqual(QualityReports.objects.count(), 0)

    def test_out_of_spec_routine_no_quarantine(self):
        from Tracker.models import PartsStatus, QualityReports
        from Tracker.services.qms.inline_capture import record_dwi_measurement

        # Out-of-spec value (nominal 1.247, +/- 0.002 → 1.260 is way out)
        sem = record_dwi_measurement(
            step_execution=self.step_execution,
            substep=self.routine_substep,
            measurement_definition=self.measurement_def,
            value=1.260,
            recorded_by=self.user,
        )
        self.assertFalse(sem.is_within_spec)
        # No QualityReports, no auto-quarantine, no NCR.
        self.assertEqual(QualityReports.objects.count(), 0)
        self.part.refresh_from_db()
        self.assertNotEqual(self.part.part_status, PartsStatus.QUARANTINED)

    def test_requires_value_or_string(self):
        from Tracker.services.qms.inline_capture import record_dwi_measurement
        with self.assertRaises(ValueError):
            record_dwi_measurement(
                step_execution=self.step_execution,
                substep=self.routine_substep,
                measurement_definition=self.measurement_def,
                recorded_by=self.user,
            )


class RecordDwiMeasurementTier2Tests(DwiPhase3BaseTestCase):
    """`is_inspection_point=True` substeps additionally create inspection
    records and fire the side-effects pipeline."""

    def test_in_spec_creates_passing_report_no_quarantine(self):
        from Tracker.models import (
            MeasurementResult,
            PartsStatus,
            QualityReports,
        )
        from Tracker.services.qms.inline_capture import record_dwi_measurement

        record_dwi_measurement(
            step_execution=self.step_execution,
            substep=self.inspection_substep,
            measurement_definition=self.measurement_def,
            value=1.247,  # in-spec
            recorded_by=self.user,
        )

        # Tier 2 row created.
        reports = QualityReports.objects.all()
        self.assertEqual(reports.count(), 1)
        self.assertEqual(reports.first().status, "PASS")

        # MeasurementResult auto-evaluated.
        mrs = MeasurementResult.objects.all()
        self.assertEqual(mrs.count(), 1)
        self.assertTrue(mrs.first().is_within_spec)

        # No auto-quarantine on PASS.
        self.part.refresh_from_db()
        self.assertNotEqual(self.part.part_status, PartsStatus.QUARANTINED)

    def test_out_of_spec_creates_failing_report_and_quarantines(self):
        from Tracker.models import PartsStatus, QualityReports
        from Tracker.services.qms.inline_capture import record_dwi_measurement

        record_dwi_measurement(
            step_execution=self.step_execution,
            substep=self.inspection_substep,
            measurement_definition=self.measurement_def,
            value=1.260,  # out of spec
            recorded_by=self.user,
        )

        report = QualityReports.objects.get()
        self.assertEqual(report.status, "FAIL")

        # Part auto-quarantined via record_quality_report_side_effects.
        self.part.refresh_from_db()
        self.assertEqual(self.part.part_status, PartsStatus.QUARANTINED)

    def test_idempotent_one_report_per_substep_execution(self):
        """Multiple captures during the same (step_execution, substep)
        share one QualityReports; each adds a MeasurementResult."""
        from Tracker.models import MeasurementResult, QualityReports
        from Tracker.services.qms.inline_capture import record_dwi_measurement

        for value in [1.246, 1.247, 1.248]:
            record_dwi_measurement(
                step_execution=self.step_execution,
                substep=self.inspection_substep,
                measurement_definition=self.measurement_def,
                value=value,
                recorded_by=self.user,
            )

        # One report, three measurements.
        self.assertEqual(QualityReports.objects.count(), 1)
        self.assertEqual(MeasurementResult.objects.count(), 3)

    def test_transition_into_fail_quarantines_late(self):
        """First in-spec captures pass; a later out-of-spec transitions the
        report to FAIL and triggers auto-quarantine."""
        from Tracker.models import PartsStatus, QualityReports
        from Tracker.services.qms.inline_capture import record_dwi_measurement

        # Three in-spec readings — report stays PASS, no quarantine.
        for value in [1.246, 1.247, 1.248]:
            record_dwi_measurement(
                step_execution=self.step_execution,
                substep=self.inspection_substep,
                measurement_definition=self.measurement_def,
                value=value,
                recorded_by=self.user,
            )
        self.part.refresh_from_db()
        self.assertNotEqual(self.part.part_status, PartsStatus.QUARANTINED)
        self.assertEqual(QualityReports.objects.get().status, "PASS")

        # Now an out-of-spec reading — report transitions to FAIL.
        record_dwi_measurement(
            step_execution=self.step_execution,
            substep=self.inspection_substep,
            measurement_definition=self.measurement_def,
            value=1.260,
            recorded_by=self.user,
        )
        self.assertEqual(QualityReports.objects.get().status, "FAIL")
        self.part.refresh_from_db()
        self.assertEqual(self.part.part_status, PartsStatus.QUARANTINED)


class SpcAdapterUnionReadTests(DwiPhase3BaseTestCase):
    """SPC adapter UNION-reads both MeasurementResult and StepExecutionMeasurement."""

    def test_normalized_rows_collect_from_both_sources(self):
        from datetime import timedelta
        from django.utils import timezone
        from Tracker.models import (
            MeasurementResult,
            QualityReports,
            StepExecutionMeasurement,
        )
        from Tracker.reports.adapters.spc import _collect_normalized_rows

        # 2 inspection-record rows (process_data-disconnected QR + 2 MRs)
        report = QualityReports.objects.create(
            tenant=self.tenant,
            step=self.step,
            part=self.part,
            detected_by=self.user,
            sampling_method="manual",
            status="PENDING",
        )
        MeasurementResult.objects.create(
            tenant=self.tenant,
            report=report,
            definition=self.measurement_def,
            value_numeric=1.247,
            created_by=self.user,
        )
        MeasurementResult.objects.create(
            tenant=self.tenant,
            report=report,
            definition=self.measurement_def,
            value_numeric=1.248,
            created_by=self.user,
        )

        # 2 process-data rows
        StepExecutionMeasurement.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            measurement_definition=self.measurement_def,
            value=1.246,
            recorded_by=self.user,
            substep=self.routine_substep,
        )
        StepExecutionMeasurement.objects.create(
            tenant=self.tenant,
            step_execution=self.step_execution,
            measurement_definition=self.measurement_def,
            value=1.249,
            recorded_by=self.user,
            substep=self.routine_substep,
        )

        end = timezone.now() + timedelta(hours=1)
        start = timezone.now() - timedelta(days=30)
        rows = _collect_normalized_rows(
            tenant=self.tenant,
            measurement_id=self.measurement_def.id,
            start=start,
            end=end,
            MeasurementResult=MeasurementResult,
            StepExecutionMeasurement=StepExecutionMeasurement,
        )

        self.assertEqual(len(rows), 4)
        # All values present, regardless of source.
        values = sorted(r.value for r in rows)
        self.assertEqual(values, [1.246, 1.247, 1.248, 1.249])
        # Rows sorted by timestamp.
        timestamps = [r.timestamp for r in rows]
        self.assertEqual(timestamps, sorted(timestamps))
