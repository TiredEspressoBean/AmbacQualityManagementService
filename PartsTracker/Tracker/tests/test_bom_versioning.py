"""
Tests for `BOM.create_new_version` (composite versioning).

Covers:
  - Status gate (only RELEASED or OBSOLETE can be revised)
  - `change_description` required (compliance — ISO 9001 4.4)
  - DRAFT-successor-exists guard with a clear error
  - approved_at / approved_by cleared on new DRAFT
  - Tenant preserved across versions
  - Archived record cannot be versioned
  - Child copy: BOMLine rows (same component_type FK — historical pinning)
  - Old version retains its own lines after new version created
  - `revision_created` signal emission
  - UniqueConstraint partial — multiple versions with same natural key coexist
"""
from __future__ import annotations

from unittest.mock import MagicMock

from Tracker.models import BOM, BOMLine, PartTypes
from Tracker.services.mes.bom import create_new_bom_version
from Tracker.signals_versioning import revision_created
from Tracker.tests.base import TenantTestCase


def _make_released_bom(tenant, user, part_type, *, revision='ZZREV-A'):
    """Build a minimal RELEASED BOM for versioning tests."""
    bom = BOM.objects.create(
        part_type=part_type,
        revision=revision,
        bom_type='ASSEMBLY',
        status='RELEASED',
        approved_by=user,
        tenant=tenant,
    )
    return bom


def _add_line(bom, component_type, *, quantity='2.0000', line_number=10):
    """Attach one BOMLine to *bom*."""
    return BOMLine.objects.create(
        bom=bom,
        component_type=component_type,
        quantity=quantity,
        unit_of_measure='EA',
        line_number=line_number,
        tenant=bom.tenant,
    )


class CreateNewBOMVersionTestCase(TenantTestCase):
    """Core versioning mechanics on BOM."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='ZZTESTBOM-PT', ID_prefix='ZZBOM-')
        self.bom = _make_released_bom(self.tenant_a, self.user_a, self.part_type)

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_creates_new_version_with_incremented_version(self):
        v2 = create_new_bom_version(
            self.bom, user=self.user_a, change_description='Added R12 line',
        )
        self.assertEqual(v2.version, 2)
        self.assertEqual(v2.status, 'DRAFT')
        self.assertEqual(v2.previous_version_id, self.bom.pk)
        self.assertTrue(v2.is_current_version)

        self.bom.refresh_from_db()
        self.assertFalse(self.bom.is_current_version)

    def test_from_obsolete_allowed(self):
        self.bom.status = 'OBSOLETE'
        self.bom.save(update_fields=['status'])

        v2 = create_new_bom_version(
            self.bom, user=self.user_a, change_description='Revive from obsolete',
        )
        self.assertEqual(v2.status, 'DRAFT')

    # ------------------------------------------------------------------
    # Guard: change_description required
    # ------------------------------------------------------------------

    def test_blank_change_description_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            create_new_bom_version(self.bom, user=self.user_a, change_description='')
        self.assertIn('change_description', str(ctx.exception))

    def test_whitespace_only_change_description_rejected(self):
        with self.assertRaises(ValueError):
            create_new_bom_version(self.bom, user=self.user_a, change_description='   ')

    # ------------------------------------------------------------------
    # Guard: status gate
    # ------------------------------------------------------------------

    def test_draft_status_rejected(self):
        draft_bom = BOM.objects.create(
            part_type=self.part_type,
            revision='ZZDRAFT',
            bom_type='ASSEMBLY',
            status='DRAFT',
            tenant=self.tenant_a,
        )
        with self.assertRaises(ValueError) as ctx:
            create_new_bom_version(
                draft_bom, user=self.user_a, change_description='Should fail',
            )
        self.assertIn('DRAFT', str(ctx.exception))

    # ------------------------------------------------------------------
    # Guard: DRAFT successor
    # ------------------------------------------------------------------

    def test_draft_successor_gives_clear_error(self):
        create_new_bom_version(
            self.bom, user=self.user_a, change_description='Rev B',
        )
        # Second attempt while a DRAFT successor already exists.
        with self.assertRaises(ValueError) as ctx:
            create_new_bom_version(
                self.bom, user=self.user_a, change_description="Rev B'",
            )
        msg = str(ctx.exception).lower()
        self.assertIn('draft revision', msg)
        self.assertIn('already exists', msg)

    # ------------------------------------------------------------------
    # Field preservation / reset
    # ------------------------------------------------------------------

    def test_tenant_preserved(self):
        v2 = create_new_bom_version(
            self.bom, user=self.user_a, change_description='Rev',
        )
        self.assertEqual(str(v2.tenant_id), str(self.bom.tenant_id))
        self.assertEqual(str(v2.tenant_id), str(self.tenant_a.id))

    def test_approved_fields_cleared(self):
        v2 = create_new_bom_version(
            self.bom, user=self.user_a, change_description='Rev',
        )
        self.assertIsNone(v2.approved_at)
        self.assertIsNone(v2.approved_by_id)

    # ------------------------------------------------------------------
    # Guard: archived
    # ------------------------------------------------------------------

    def test_archived_record_cannot_be_versioned(self):
        self.bom.archived = True
        self.bom.save(update_fields=['archived'])
        with self.assertRaises(ValueError):
            create_new_bom_version(
                self.bom, user=self.user_a, change_description='Should fail',
            )


class BOMLineCopyTestCase(TenantTestCase):
    """BOMLine rows are copied to the new version."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='ZZBOMLINE-PT', ID_prefix='ZZBML-')
        self.comp_type = PartTypes.objects.create(name='ZZBOMLINE-COMP', ID_prefix='ZZCMP-')
        self.bom = _make_released_bom(self.tenant_a, self.user_a, self.part_type)
        self.line = _add_line(self.bom, self.comp_type)

    def test_bom_lines_copied_to_new_version(self):
        v2 = create_new_bom_version(
            self.bom, user=self.user_a, change_description='Added component',
        )
        v2_lines = list(BOMLine.objects.filter(bom=v2))
        self.assertEqual(len(v2_lines), 1)
        v2_line = v2_lines[0]
        self.assertEqual(v2_line.component_type_id, self.line.component_type_id)
        # Normalize Decimal-vs-string to handle whichever type the setup
        # fixture used for quantity.
        self.assertEqual(str(v2_line.quantity), str(self.line.quantity))
        self.assertEqual(v2_line.unit_of_measure, self.line.unit_of_measure)
        self.assertEqual(v2_line.line_number, self.line.line_number)

    def test_bom_lines_preserve_component_type_fk(self):
        """Historical pinning: new BOMLine FK points at the same PartType version
        that was current at copy time."""
        v2 = create_new_bom_version(
            self.bom, user=self.user_a, change_description='Rev',
        )
        v2_line = BOMLine.objects.get(bom=v2)
        # FK reference preserved — same PartType PK.
        self.assertEqual(v2_line.component_type_id, self.comp_type.pk)

    def test_old_version_retains_its_lines(self):
        create_new_bom_version(
            self.bom, user=self.user_a, change_description='Rev',
        )
        # v1 must still own its original line.
        v1_lines = list(BOMLine.objects.filter(bom=self.bom))
        self.assertEqual(len(v1_lines), 1)
        self.assertEqual(v1_lines[0].pk, self.line.pk)


class BOMVersioningSignalTestCase(TenantTestCase):
    """`revision_created` fires on successful BOM versioning."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='ZZBOMSG-PT', ID_prefix='ZZSGN-')
        self.bom = _make_released_bom(self.tenant_a, self.user_a, self.part_type)
        self.received = MagicMock()
        revision_created.connect(self.received, sender=BOM)

    def tearDown(self):
        revision_created.disconnect(self.received, sender=BOM)
        super().tearDown()

    def test_revision_created_signal_fires_with_correct_kwargs(self):
        v2 = create_new_bom_version(
            self.bom, user=self.user_a, change_description='Rev B — safety update',
        )
        self.received.assert_called_once()
        kwargs = self.received.call_args.kwargs
        self.assertEqual(kwargs['sender'], BOM)
        self.assertEqual(kwargs['old_version'].pk, self.bom.pk)
        self.assertEqual(kwargs['new_version'].pk, v2.pk)
        self.assertEqual(kwargs['user'], self.user_a)
        self.assertEqual(kwargs['change_description'], 'Rev B — safety update')


class UniqueConstraintPartialTestCase(TenantTestCase):
    """Partial UniqueConstraint allows multiple versions of the same natural key."""

    def test_multiple_versions_with_same_natural_key_coexist(self):
        """Two rows with identical (tenant, part_type, revision, bom_type) must
        coexist once the constraint is partial on is_current_version=True."""
        part_type = PartTypes.objects.create(name='ZZCONSTRAINT-PT', ID_prefix='ZZCON-')
        bom_v1 = _make_released_bom(
            self.tenant_a, self.user_a, part_type, revision='ZZREV-UC',
        )
        # This call previously would violate the unconditional unique constraint;
        # the partial constraint (is_current_version=True only) permits it.
        v2 = create_new_bom_version(
            bom_v1, user=self.user_a, change_description='Constraint test rev',
        )
        self.assertEqual(v2.version, 2)
        # Both rows exist with the same natural key values.
        all_rows = list(
            BOM.all_tenants.filter(
                tenant=self.tenant_a,
                part_type=part_type,
                revision='ZZREV-UC',
                bom_type='ASSEMBLY',
            )
        )
        self.assertEqual(len(all_rows), 2)
        current_rows = [r for r in all_rows if r.is_current_version]
        self.assertEqual(len(current_rows), 1)
        self.assertEqual(current_rows[0].pk, v2.pk)
