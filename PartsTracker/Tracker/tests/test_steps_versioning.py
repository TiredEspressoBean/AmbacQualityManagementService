"""
Tests for `Steps.create_new_version` (composite).

Covers:
  - `change_description` required (ISO 9001 4.4 compliance)
  - No status gate — Steps have no DRAFT/APPROVED lifecycle; any current,
    non-archived step can be versioned.
  - Base-layer guards: archived step, non-current version
  - Tenant preserved across versions
  - Field overrides applied on new version
  - Child copy: StepMeasurementRequirement (three Control Plan fields)
  - Child copy: StepRequirement (all config fields)
  - Cross-cutting TrainingRequirement: step-owned only — process-linked and
    equipment_type-linked rows must NOT be copied.
  - Documents GenericRelation copied (fresh rows, same file_name, approval
    status carried forward for unchanged attachments)
  - `revision_created` signal fires with correct kwargs
"""
from __future__ import annotations

from unittest.mock import MagicMock

from django.contrib.contenttypes.models import ContentType

from Tracker.models import (
    Documents,
    EquipmentType,
    MeasurementDefinition,
    PartTypes,
    Processes,
    ProcessStatus,
    RequirementType,
    Steps,
    StepMeasurementRequirement,
    StepRequirement,
    StepTiming,
    Substep,
    SubstepResource,
    SubstepTranslation,
    TrainingRequirement,
    TrainingType,
)
from Tracker.services.mes.steps import create_new_step_version
from Tracker.signals_versioning import revision_created
from Tracker.tests.base import TenantTestCase


# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------

def _make_step(part_type, name='Leak Test'):
    """Create a minimal step for the given part_type."""
    return Steps.objects.create(
        name=name,
        part_type=part_type,
        pass_threshold=1.0,
    )


def _make_measurement_def(step, label='OD'):
    """Create a MeasurementDefinition attached to a step."""
    return MeasurementDefinition.objects.create(
        step=step,
        label=label,
        type='NUMERIC',
        unit='mm',
    )


# ---------------------------------------------------------------------------
# Core versioning mechanics
# ---------------------------------------------------------------------------

class CreateNewStepVersionTestCase(TenantTestCase):
    """Core versioning behaviour for Steps."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='Step_PT', ID_prefix='SPT-')
        self.step = _make_step(self.part_type)

    def test_creates_new_version_with_incremented_version_number(self):
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev B',
        )
        self.assertEqual(v2.version, 2)
        self.assertTrue(v2.is_current_version)
        self.assertEqual(v2.previous_version_id, self.step.pk)

        self.step.refresh_from_db()
        self.assertFalse(self.step.is_current_version)

    def test_change_description_required_raises_on_blank(self):
        with self.assertRaises(ValueError) as ctx:
            create_new_step_version(
                self.step, user=self.user_a, change_description='',
            )
        self.assertIn('change_description', str(ctx.exception))

    def test_change_description_required_raises_on_whitespace(self):
        with self.assertRaises(ValueError):
            create_new_step_version(
                self.step, user=self.user_a, change_description='   ',
            )

    def test_tenant_preserved_across_version(self):
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        self.assertEqual(str(v2.tenant_id), str(self.step.tenant_id))
        self.assertEqual(str(v2.tenant_id), str(self.tenant_a.id))

    def test_field_override_applied_on_new_version(self):
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
            name='Leak Test v2',
        )
        self.assertEqual(v2.name, 'Leak Test v2')
        # Original is unchanged
        self.step.refresh_from_db()
        self.assertEqual(self.step.name, 'Leak Test')

    def test_no_status_gate_any_step_can_be_versioned(self):
        """Steps have no status field; the base archived/is_current guards are the
        only gates. A plain step (no status) should version without error."""
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        self.assertEqual(v2.version, 2)

    def test_archived_step_raises(self):
        self.step.archived = True
        self.step.save(update_fields=['archived'])
        with self.assertRaises(ValueError) as ctx:
            create_new_step_version(
                self.step, user=self.user_a, change_description='Rev',
            )
        self.assertIn('archived', str(ctx.exception).lower())

    def test_non_current_version_raises(self):
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        # self.step is now the non-current v1
        with self.assertRaises(ValueError) as ctx:
            create_new_step_version(
                self.step, user=self.user_a, change_description='Rev again',
            )
        self.assertIn('current version', str(ctx.exception).lower())


# ---------------------------------------------------------------------------
# StepMeasurementRequirement child copy
# ---------------------------------------------------------------------------

class StepMeasurementRequirementCopyTestCase(TenantTestCase):
    """SMR rows are copied to the new version with the same measurement FK."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='SMR_PT', ID_prefix='SMR-')
        self.step = _make_step(self.part_type, name='SMR Step')
        self.mdef = _make_measurement_def(self.step, label='Wall Thickness')
        self.smr = StepMeasurementRequirement.objects.create(
            step=self.step,
            measurement=self.mdef,
            is_mandatory=True,
            sequence=1,
            characteristic_number='B01',
            tolerance_upper_override=0.05,
            tolerance_lower_override=-0.05,
        )

    def test_smr_copied_to_new_version_with_same_measurement_fk(self):
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        v2_smrs = StepMeasurementRequirement.objects.filter(step=v2)
        self.assertEqual(v2_smrs.count(), 1)
        v2_smr = v2_smrs.first()
        # Same measurement FK — historically pinned
        self.assertEqual(v2_smr.measurement_id, self.mdef.pk)
        # Control Plan metadata carried forward
        self.assertEqual(v2_smr.characteristic_number, 'B01')
        self.assertEqual(v2_smr.tolerance_upper_override, 0.05)
        self.assertNotEqual(v2_smr.pk, self.smr.pk)

    def test_old_version_retains_its_smr_rows(self):
        create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        # v1's SMR rows are untouched
        self.assertEqual(
            StepMeasurementRequirement.objects.filter(step=self.step).count(), 1,
        )

    def test_multiple_smrs_all_copied(self):
        mdef2 = _make_measurement_def(self.step, label='Inner Diameter')
        StepMeasurementRequirement.objects.create(
            step=self.step,
            measurement=mdef2,
            sequence=2,
        )
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        self.assertEqual(StepMeasurementRequirement.objects.filter(step=v2).count(), 2)


# ---------------------------------------------------------------------------
# StepRequirement child copy
# ---------------------------------------------------------------------------

class StepRequirementCopyTestCase(TenantTestCase):
    """StepRequirement rows are copied to the new version with all config fields."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='SReq_PT', ID_prefix='SR-')
        self.step = _make_step(self.part_type, name='SReq Step')
        self.req = StepRequirement.objects.create(
            step=self.step,
            requirement_type=RequirementType.SIGNOFF,
            name='Supervisor signoff',
            description='Must be signed off by a supervisor.',
            is_mandatory=True,
            order=1,
            config={'role': 'supervisor'},
        )

    def test_requirement_copied_to_new_version_with_correct_fields(self):
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        v2_reqs = StepRequirement.objects.filter(step=v2)
        self.assertEqual(v2_reqs.count(), 1)
        v2_req = v2_reqs.first()
        self.assertEqual(v2_req.requirement_type, RequirementType.SIGNOFF)
        self.assertEqual(v2_req.name, 'Supervisor signoff')
        self.assertEqual(v2_req.config, {'role': 'supervisor'})
        self.assertNotEqual(v2_req.pk, self.req.pk)

    def test_old_version_retains_its_requirement_rows(self):
        create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        self.assertEqual(
            StepRequirement.objects.filter(step=self.step).count(), 1,
        )

    def test_multiple_requirements_all_copied(self):
        StepRequirement.objects.create(
            step=self.step,
            requirement_type=RequirementType.QA_APPROVAL,
            name='QA approval',
            order=2,
        )
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        self.assertEqual(StepRequirement.objects.filter(step=v2).count(), 2)


# ---------------------------------------------------------------------------
# Substep + SubstepResource / SubstepTranslation child copy
# ---------------------------------------------------------------------------

class SubstepCopyOnStepVersioningTestCase(TenantTestCase):
    """Substeps and their child rows (SubstepResource, SubstepTranslation) are
    copied to the new Step version. Regression guard: the SubstepResource copy
    previously referenced fields that don't exist on the model
    (`kind`/`document`/`threed_model`/…), a latent AttributeError that only
    fired when a versioned step actually had a resource row."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='Sub_PT', ID_prefix='SUB-')
        self.step = _make_step(self.part_type, name='Sub Step')
        self.eq_type = EquipmentType.objects.create(
            name='Digital micrometer 0-1 in', description='Micrometer',
        )
        self.sub = Substep.objects.create(
            tenant=self.tenant_a, step=self.step, order=0, title='Measure OD',
            is_optional=False,
        )
        self.res = SubstepResource.objects.create(
            tenant=self.tenant_a, substep=self.sub, equipment_type=self.eq_type,
            quantity='1.0000', notes='Calibrated gage required', required=True,
        )
        self.tr = SubstepTranslation.objects.create(
            tenant=self.tenant_a, substep=self.sub, language='es',
            title='Medir DE', body_blocks=[],
        )

    def test_substep_and_resource_copied_to_new_version(self):
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        v2_subs = Substep.objects.filter(step=v2)
        self.assertEqual(v2_subs.count(), 1)
        v2_sub = v2_subs.first()
        self.assertNotEqual(v2_sub.pk, self.sub.pk)
        self.assertEqual(v2_sub.title, 'Measure OD')

        # Regression: this copy used to raise AttributeError on nonexistent fields.
        v2_resources = SubstepResource.objects.filter(substep=v2_sub)
        self.assertEqual(v2_resources.count(), 1)
        v2_res = v2_resources.first()
        self.assertNotEqual(v2_res.pk, self.res.pk)
        self.assertEqual(v2_res.equipment_type_id, self.eq_type.pk)
        self.assertEqual(v2_res.notes, 'Calibrated gage required')
        self.assertTrue(v2_res.required)

    def test_substep_translation_copied_to_new_version(self):
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        v2_sub = Substep.objects.filter(step=v2).first()
        v2_trs = SubstepTranslation.objects.filter(substep=v2_sub)
        self.assertEqual(v2_trs.count(), 1)
        self.assertNotEqual(v2_trs.first().pk, self.tr.pk)
        self.assertEqual(v2_trs.first().language, 'es')
        self.assertEqual(v2_trs.first().title, 'Medir DE')

    def test_old_version_retains_its_substep_rows(self):
        create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        self.assertEqual(Substep.objects.filter(step=self.step).count(), 1)
        self.assertEqual(
            SubstepResource.objects.filter(substep=self.sub).count(), 1,
        )


# ---------------------------------------------------------------------------
# TrainingRequirement cross-cutting (CRITICAL)
# ---------------------------------------------------------------------------

class TrainingRequirementCrossCuttingTestCase(TenantTestCase):
    """TrainingRequirement cross-cutting ownership rules.

    When a Step versions, only TrainingRequirement rows where `step=self` AND
    `process` IS NULL AND `equipment_type` IS NULL are copied. Rows linked via
    `process` or `equipment_type` belong to those aggregates' version lifecycles
    and must not be duplicated here.
    """

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='TR_PT', ID_prefix='TR-')
        self.step = _make_step(self.part_type, name='TR Step')
        self.training_type = TrainingType.objects.create(
            name='CMM Operation',
            description='Coordinate measuring machine',
        )

    def test_step_linked_training_requirement_copied(self):
        """TrainingRequirement with step=self and no process/equipment_type is copied."""
        tr = TrainingRequirement.objects.create(
            step=self.step,
            training_type=self.training_type,
            notes='Per WI-042',
            tenant=self.tenant_a,
        )
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        v2_trs = TrainingRequirement.objects.filter(step=v2)
        self.assertEqual(v2_trs.count(), 1)
        v2_tr = v2_trs.first()
        self.assertEqual(v2_tr.training_type_id, self.training_type.pk)
        self.assertEqual(v2_tr.notes, 'Per WI-042')
        self.assertNotEqual(v2_tr.pk, tr.pk)

    def test_process_linked_training_requirement_not_copied(self):
        """TrainingRequirement with process=X and step=None must NOT be copied
        when Steps versions — it belongs to the Process version lifecycle."""
        process = Processes.objects.create(
            name='Assembly',
            part_type=self.part_type,
            status=ProcessStatus.DRAFT,
        )
        TrainingRequirement.objects.create(
            process=process,
            training_type=self.training_type,
            notes='Process-owned TR',
            tenant=self.tenant_a,
        )
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        # No TrainingRequirement should be linked to the new step version
        self.assertEqual(TrainingRequirement.objects.filter(step=v2).count(), 0)

    def test_equipment_type_linked_training_requirement_not_copied(self):
        """TrainingRequirement with equipment_type=X and step=None must NOT be
        copied when Steps versions — it belongs to the EquipmentType lifecycle."""
        eq_type = EquipmentType.objects.create(
            name='CMM Machine',
            description='CMM',
        )
        TrainingRequirement.objects.create(
            equipment_type=eq_type,
            training_type=self.training_type,
            notes='Equipment-owned TR',
            tenant=self.tenant_a,
        )
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        self.assertEqual(TrainingRequirement.objects.filter(step=v2).count(), 0)

    def test_mixed_step_and_process_training_requirements_copy_only_step_linked(self):
        """With a mix of step-owned and process-owned TRs, only the step-owned
        row is copied to the new version."""
        training_type_2 = TrainingType.objects.create(
            name='Blueprint Reading',
            description='Drawing interpretation',
        )
        # Step-owned — should be copied
        TrainingRequirement.objects.create(
            step=self.step,
            training_type=self.training_type,
            notes='Step-owned',
            tenant=self.tenant_a,
        )
        # Process-owned — must NOT be copied
        process = Processes.objects.create(
            name='Rework Process',
            part_type=self.part_type,
            status=ProcessStatus.DRAFT,
        )
        TrainingRequirement.objects.create(
            process=process,
            training_type=training_type_2,
            notes='Process-owned',
            tenant=self.tenant_a,
        )

        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )

        v2_trs = TrainingRequirement.objects.filter(step=v2)
        self.assertEqual(v2_trs.count(), 1)
        self.assertEqual(v2_trs.first().training_type_id, self.training_type.pk)
        self.assertEqual(v2_trs.first().notes, 'Step-owned')


# ---------------------------------------------------------------------------
# Documents GenericRelation copy
# ---------------------------------------------------------------------------

class DocumentsCopyOnStepVersioningTestCase(TenantTestCase):
    """Documents attached to a Step via GenericRelation are copied to the new
    version as fresh Document rows (same file_name, same storage, approval
    status carried forward)."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='DocStep_PT', ID_prefix='DS-')
        self.step = _make_step(self.part_type, name='Doc Step')
        step_ct = ContentType.objects.get_for_model(Steps)
        self.doc = Documents.objects.create(
            content_type=step_ct,
            object_id=self.step.pk,
            file_name='step-SOP-rev-A.pdf',
            is_image=False,
            classification='INTERNAL',
            status='APPROVED',
            approved_by=self.user_a,
        )

    def test_document_copied_to_new_version(self):
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        step_ct = ContentType.objects.get_for_model(Steps)
        v2_docs = Documents.objects.filter(content_type=step_ct, object_id=v2.pk)
        self.assertEqual(v2_docs.count(), 1)
        v2_doc = v2_docs.first()
        self.assertNotEqual(v2_doc.pk, self.doc.pk)
        self.assertEqual(v2_doc.file_name, 'step-SOP-rev-A.pdf')

    def test_v2_document_carries_approval_forward(self):
        """An unchanged attachment keeps its APPROVED status and approver on
        the new Step version — revving the step does not force re-signing
        identical documents."""
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        step_ct = ContentType.objects.get_for_model(Steps)
        v2_doc = Documents.objects.filter(content_type=step_ct, object_id=v2.pk).first()
        self.assertEqual(v2_doc.status, 'APPROVED')
        self.assertEqual(v2_doc.approved_by, self.user_a)

    def test_v1_document_unchanged_after_versioning(self):
        create_new_step_version(
            self.step, user=self.user_a, change_description='Rev',
        )
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, 'APPROVED')
        self.assertEqual(self.doc.object_id, str(self.step.pk))


# ---------------------------------------------------------------------------
# revision_created signal
# ---------------------------------------------------------------------------

class RevisionSignalTestCase(TenantTestCase):
    """`revision_created` fires on successful step versioning."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='Sig_PT', ID_prefix='SIG-')
        self.step = _make_step(self.part_type, name='Signal Step')
        self.received = MagicMock()
        revision_created.connect(self.received, sender=Steps)

    def tearDown(self):
        revision_created.disconnect(self.received, sender=Steps)
        super().tearDown()

    def test_signal_fires_with_expected_kwargs(self):
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Added new requirement',
        )
        self.received.assert_called_once()
        kwargs = self.received.call_args.kwargs
        self.assertEqual(kwargs['sender'], Steps)
        self.assertEqual(kwargs['old_version'].pk, self.step.pk)
        self.assertEqual(kwargs['new_version'].pk, v2.pk)
        self.assertEqual(kwargs['user'], self.user_a)
        self.assertEqual(kwargs['change_description'], 'Added new requirement')


class StepTimingCopyOnStepVersioningTestCase(TenantTestCase):
    """StepTiming is child copy 4 in `create_new_step_version`.

    Timing is step behaviour, so it forks with the step. Before it joined the copy
    list a new version had no timing row at all, and that failure is silent rather
    than loud: the solver sizes an untimed op to zero minutes and `rccp._step_hours`
    returns 0.0, so a versioned step simply becomes free.
    """

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='Timing_PT', ID_prefix='TIM-')
        self.step = _make_step(self.part_type, name='Bore')
        self.timing = StepTiming.objects.create(
            step=self.step,
            setup_minutes=25.0,
            cycle_time_minutes=4.5,
            load_unload_per_piece=1.25,
            attention_type='load_unload',
            external_setup_minutes=10.0,
        )

    def test_new_version_carries_every_timing_field(self):
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev B')

        t2 = StepTiming.objects.get(step=v2)
        self.assertEqual(t2.setup_minutes, 25.0)
        self.assertEqual(t2.cycle_time_minutes, 4.5)
        self.assertEqual(t2.load_unload_per_piece, 1.25)
        self.assertEqual(t2.attention_type, 'load_unload')
        self.assertEqual(t2.external_setup_minutes, 10.0)

    def test_timing_is_copied_not_moved(self):
        """`StepTiming.step` is a OneToOne, so a MOVE would strip v1 of its timing and
        make the superseded version read as free — which is what history is for."""
        v2 = create_new_step_version(
            self.step, user=self.user_a, change_description='Rev B')

        self.assertNotEqual(StepTiming.objects.get(step=v2).pk, self.timing.pk)
        self.timing.refresh_from_db()
        self.assertEqual(self.timing.step_id, self.step.pk)
        self.assertEqual(StepTiming.objects.filter(step_id__in=[self.step.pk, v2.pk]).count(), 2)

    def test_step_without_timing_versions_cleanly(self):
        """An untimed step is a real state, not a broken one — versioning it must not
        raise, and must not invent a row."""
        bare = _make_step(self.part_type, name='Deburr')
        v2 = create_new_step_version(
            bare, user=self.user_a, change_description='Rev B')
        self.assertFalse(StepTiming.objects.filter(step=v2).exists())

    def test_serializer_timing_edit_lands_on_the_row_the_update_returns(self):
        """`timing` is popped out before the versioning diff, so a timing-only edit has
        no versioning field to fork on and updates the step in place. What matters is
        that the write follows whatever row `apply_versioned_update` hands back — when a
        fork does happen (a versioned scalar changed too), timing must land on the NEW
        row or the edit silently applies to a superseded one.
        """
        from Tracker.serializers.mes_lite import StepsSerializer

        ser = StepsSerializer(
            self.step,
            data={'timing': {'setup_minutes': 99.0, 'cycle_time_minutes': 7.0}},
            partial=True,
        )
        ser.is_valid(raise_exception=True)
        updated = ser.save()

        self.assertEqual(updated.pk, self.step.pk, "timing alone should not fork")
        t = StepTiming.objects.get(step=updated)
        self.assertEqual(t.setup_minutes, 99.0)
        self.assertEqual(t.cycle_time_minutes, 7.0)
        # Untouched keys survive a partial write rather than resetting to the default.
        self.assertEqual(t.attention_type, 'load_unload')

    def test_serializer_null_timing_clears_the_row(self):
        """`timing: null` has to be expressible: the solver sizes an untimed op to zero
        and RCCP reads it as free, so "no timing" is a state a planner may intend."""
        from Tracker.serializers.mes_lite import StepsSerializer

        from Tracker.services.scheduling.data import get_step_timings

        ser = StepsSerializer(self.step, data={'timing': None}, partial=True)
        ser.is_valid(raise_exception=True)
        updated = ser.save()

        # Asserted against what PLANNING sees, not against row existence. Hard delete is
        # disabled repo-wide, so the clear soft-deletes; the row is still there. What has
        # to be true is that the solver and RCCP stop reading it — which is exactly what
        # was broken: every reader took `.objects` unfiltered, so a cleared timing kept
        # sizing the op and the clear silently did nothing.
        self.assertTrue(StepTiming.objects.filter(step=updated, archived=True).exists())
        # Every step gets an entry (the chain falls back to history, then to defaults),
        # so the test is on the VALUES: the cleared row must stop supplying its 25-minute
        # setup. That is what silently kept working before — the clear saved, and the
        # solver went on sizing the op exactly as it had.
        resolved = get_step_timings(self.tenant_a)[updated.pk]
        self.assertEqual(resolved.setup_minutes, 0.0)
        self.assertEqual(resolved.cycle_time_minutes, 0.0)
        self.assertEqual(resolved.cycle_source, 'none')
