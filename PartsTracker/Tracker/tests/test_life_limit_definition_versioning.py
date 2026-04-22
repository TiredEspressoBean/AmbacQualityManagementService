"""
Tests for `LifeLimitDefinition.create_new_version` (composite versioning).

Covers:
  - `change_description` required (compliance — AS9100D §8.3)
  - New version: incremented version, previous_version link, is_current_version flip
  - No status gate (LifeLimitDefinition is a pure spec model with no approval workflow)
  - Child copy: PartTypeLifeLimit rows copied with same part_type FKs
  - v1's children are untouched after versioning
  - `revision_created` signal emission
  - Partial UniqueConstraint allows same name across versions
"""
from __future__ import annotations

from unittest.mock import MagicMock

from Tracker.models import LifeLimitDefinition, PartTypeLifeLimit, PartTypes
from Tracker.services.life_tracking.life_limit_definition import (
    create_new_life_limit_definition_version,
)
from Tracker.signals_versioning import revision_created
from Tracker.tests.base import TenantTestCase


def _make_definition(name='Flight Cycles', unit='cycles', unit_label='Cycles', hard_limit=20000):
    """Create a minimal LifeLimitDefinition for the current tenant context."""
    return LifeLimitDefinition.objects.create(
        name=name,
        unit=unit,
        unit_label=unit_label,
        hard_limit=hard_limit,
    )


class CreateNewLifeLimitDefinitionVersionTestCase(TenantTestCase):
    """Core versioning mechanics on LifeLimitDefinition."""

    def setUp(self):
        super().setUp()
        self.definition = _make_definition()

    def test_creates_new_version_with_incremented_version(self):
        v2 = create_new_life_limit_definition_version(
            self.definition,
            user=self.user_a,
            change_description='Rev B — tighten hard limit to 18000',
        )
        self.assertEqual(v2.version, 2)
        self.assertEqual(v2.previous_version_id, self.definition.pk)
        self.assertTrue(v2.is_current_version)

        self.definition.refresh_from_db()
        self.assertFalse(self.definition.is_current_version)

    def test_scalar_fields_carried_forward(self):
        v2 = create_new_life_limit_definition_version(
            self.definition,
            user=self.user_a,
            change_description='Carry forward test',
        )
        self.assertEqual(v2.name, self.definition.name)
        self.assertEqual(v2.unit, self.definition.unit)
        self.assertEqual(v2.unit_label, self.definition.unit_label)
        self.assertEqual(v2.hard_limit, self.definition.hard_limit)

    def test_field_update_applied_to_new_version(self):
        v2 = create_new_life_limit_definition_version(
            self.definition,
            user=self.user_a,
            change_description='Update hard limit',
            hard_limit=18000,
        )
        self.assertEqual(v2.hard_limit, 18000)
        # v1 unchanged
        self.definition.refresh_from_db()
        self.assertEqual(self.definition.hard_limit, 20000)

    def test_tenant_preserved(self):
        v2 = create_new_life_limit_definition_version(
            self.definition,
            user=self.user_a,
            change_description='Tenant check',
        )
        self.assertEqual(str(v2.tenant_id), str(self.definition.tenant_id))
        self.assertEqual(str(v2.tenant_id), str(self.tenant_a.id))

    def test_blank_change_description_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            create_new_life_limit_definition_version(
                self.definition,
                user=self.user_a,
                change_description='',
            )
        self.assertIn('change_description', str(ctx.exception))

    def test_whitespace_only_change_description_rejected(self):
        with self.assertRaises(ValueError):
            create_new_life_limit_definition_version(
                self.definition,
                user=self.user_a,
                change_description='   ',
            )

    def test_model_delegate_calls_service(self):
        """LifeLimitDefinition.create_new_version() thin delegate works end-to-end."""
        v2 = self.definition.create_new_version(
            user=self.user_a,
            change_description='Via delegate',
        )
        self.assertEqual(v2.version, 2)
        self.assertTrue(v2.is_current_version)

    def test_not_current_version_raises(self):
        """Base guard: cannot create a version from a non-current row."""
        create_new_life_limit_definition_version(
            self.definition,
            user=self.user_a,
            change_description='Rev B',
        )
        # definition is now is_current_version=False
        with self.assertRaises(ValueError) as ctx:
            create_new_life_limit_definition_version(
                self.definition,
                user=self.user_a,
                change_description='Rev C from stale v1',
            )
        self.assertIn('current version', str(ctx.exception).lower())


class PartTypeLifeLimitCopyTestCase(TenantTestCase):
    """PartTypeLifeLimit junction rows are copied; part_type FKs preserved."""

    def setUp(self):
        super().setUp()
        self.part_type_a = PartTypes.objects.create(name='LLD-PartTypeA', ID_prefix='LDA-')
        self.part_type_b = PartTypes.objects.create(name='LLD-PartTypeB', ID_prefix='LDB-')
        self.definition = _make_definition(name='LLD Shot Count', unit='shots', unit_label='Shots')
        PartTypeLifeLimit.objects.create(
            definition=self.definition,
            part_type=self.part_type_a,
            is_required=True,
        )
        PartTypeLifeLimit.objects.create(
            definition=self.definition,
            part_type=self.part_type_b,
            is_required=False,
        )

    def test_children_copied_to_new_version(self):
        v2 = create_new_life_limit_definition_version(
            self.definition,
            user=self.user_a,
            change_description='Rev B',
        )
        v2_links = list(v2.part_type_links.all())
        self.assertEqual(len(v2_links), 2)

    def test_part_type_fks_preserved(self):
        v2 = create_new_life_limit_definition_version(
            self.definition,
            user=self.user_a,
            change_description='FK pinning check',
        )
        v1_part_type_ids = set(
            self.definition.part_type_links.values_list('part_type_id', flat=True)
        )
        v2_part_type_ids = set(
            v2.part_type_links.values_list('part_type_id', flat=True)
        )
        self.assertEqual(v1_part_type_ids, v2_part_type_ids)

    def test_v1_children_unchanged_after_versioning(self):
        original_count = self.definition.part_type_links.count()

        create_new_life_limit_definition_version(
            self.definition,
            user=self.user_a,
            change_description='Rev B',
        )

        self.definition.refresh_from_db()
        self.assertEqual(self.definition.part_type_links.count(), original_count)

    def test_child_rows_are_new_pks(self):
        v2 = create_new_life_limit_definition_version(
            self.definition,
            user=self.user_a,
            change_description='Distinct PKs check',
        )
        v1_pks = set(self.definition.part_type_links.values_list('pk', flat=True))
        v2_pks = set(v2.part_type_links.values_list('pk', flat=True))
        self.assertTrue(v1_pks.isdisjoint(v2_pks))


class RevisionSignalTestCase(TenantTestCase):
    """`revision_created` fires on successful versioning with correct kwargs."""

    def setUp(self):
        super().setUp()
        self.definition = _make_definition(name='LLD Signal Test Cycles')
        self.received = MagicMock()
        revision_created.connect(self.received, sender=LifeLimitDefinition)

    def tearDown(self):
        revision_created.disconnect(self.received, sender=LifeLimitDefinition)
        super().tearDown()

    def test_signal_fires_with_expected_kwargs(self):
        v2 = create_new_life_limit_definition_version(
            self.definition,
            user=self.user_a,
            change_description='Signal check',
        )
        self.received.assert_called_once()
        kwargs = self.received.call_args.kwargs
        self.assertEqual(kwargs['sender'], LifeLimitDefinition)
        self.assertEqual(kwargs['old_version'].pk, self.definition.pk)
        self.assertEqual(kwargs['new_version'].pk, v2.pk)
        self.assertEqual(kwargs['user'], self.user_a)
        self.assertEqual(kwargs['change_description'], 'Signal check')


class UniqueConstraintPartialTestCase(TenantTestCase):
    """Partial UniqueConstraint allows the same name across versions."""

    def test_same_name_allowed_for_historical_version(self):
        """After versioning, v1 (is_current_version=False) and v2 share the
        same tenant+name — the partial constraint must not reject v2's insert."""
        definition = _make_definition(name='LLD Partial Constraint Cycles')

        # Should not raise IntegrityError — v1 flips is_current_version=False
        # before v2 is inserted.
        v2 = create_new_life_limit_definition_version(
            definition,
            user=self.user_a,
            change_description='Constraint test',
        )

        self.assertEqual(v2.name, definition.name)
        self.assertTrue(v2.is_current_version)
        definition.refresh_from_db()
        self.assertFalse(definition.is_current_version)
