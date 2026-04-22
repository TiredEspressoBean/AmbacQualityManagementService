"""
Tests for `MilestoneTemplate.create_new_version` (composite versioning).

Covers:
  - `change_description` required (compliance — ISO 9001 4.4)
  - New version: incremented version, previous_version link, is_current_version flip
  - No status gate (MilestoneTemplate is a pure config model with no approval workflow)
  - Child copy: Milestone rows copied with new template FK
  - display_order and is_active flags preserved across copy
  - v1's Milestone rows are untouched after versioning
  - Orders.current_milestone stays pinned to v1's Milestone after versioning
  - `revision_created` signal emission
  - Partial UniqueConstraint allows same name across versions
"""
from __future__ import annotations

from unittest.mock import MagicMock

from Tracker.models.mes_lite import MilestoneTemplate, Milestone, Orders
from Tracker.services.mes.milestone_template import create_new_milestone_template_version
from Tracker.signals_versioning import revision_created
from Tracker.tests.base import TenantTestCase


def _make_template(name='Standard Order Process', description=''):
    """Create a minimal MilestoneTemplate scoped to the current tenant context."""
    return MilestoneTemplate.objects.create(
        name=name,
        description=description,
    )


def _add_milestone(template, name, display_order, customer_display_name='', is_active=True):
    """Add a Milestone to a template."""
    return Milestone.objects.create(
        template=template,
        name=name,
        customer_display_name=customer_display_name,
        display_order=display_order,
        is_active=is_active,
        tenant=template.tenant,
    )


class CreateNewMilestoneTemplateVersionTestCase(TenantTestCase):
    """Core versioning mechanics on MilestoneTemplate."""

    def setUp(self):
        super().setUp()
        self.template = _make_template(name='MT-Core Test Template')

    def test_creates_new_version_with_incremented_version(self):
        v2 = create_new_milestone_template_version(
            self.template,
            user=self.user_a,
            change_description='Rev B — add design review gate',
        )
        self.assertEqual(v2.version, 2)
        self.assertEqual(v2.previous_version_id, self.template.pk)
        self.assertTrue(v2.is_current_version)

        self.template.refresh_from_db()
        self.assertFalse(self.template.is_current_version)

    def test_scalar_fields_carried_forward(self):
        v2 = create_new_milestone_template_version(
            self.template,
            user=self.user_a,
            change_description='Carry forward test',
        )
        self.assertEqual(v2.name, self.template.name)
        self.assertEqual(v2.description, self.template.description)

    def test_field_update_applied_to_new_version(self):
        v2 = create_new_milestone_template_version(
            self.template,
            user=self.user_a,
            change_description='Update description',
            description='Updated description for v2',
        )
        self.assertEqual(v2.description, 'Updated description for v2')
        self.template.refresh_from_db()
        self.assertEqual(self.template.description, '')

    def test_tenant_preserved(self):
        v2 = create_new_milestone_template_version(
            self.template,
            user=self.user_a,
            change_description='Tenant check',
        )
        self.assertEqual(str(v2.tenant_id), str(self.template.tenant_id))
        self.assertEqual(str(v2.tenant_id), str(self.tenant_a.id))

    def test_blank_change_description_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            create_new_milestone_template_version(
                self.template,
                user=self.user_a,
                change_description='',
            )
        self.assertIn('change_description', str(ctx.exception))

    def test_whitespace_only_change_description_rejected(self):
        with self.assertRaises(ValueError):
            create_new_milestone_template_version(
                self.template,
                user=self.user_a,
                change_description='   ',
            )

    def test_model_delegate_calls_service(self):
        """MilestoneTemplate.create_new_version() thin delegate works end-to-end."""
        v2 = self.template.create_new_version(
            user=self.user_a,
            change_description='Via delegate',
        )
        self.assertEqual(v2.version, 2)
        self.assertTrue(v2.is_current_version)

    def test_not_current_version_raises(self):
        """Base guard: cannot create a version from a non-current row."""
        create_new_milestone_template_version(
            self.template,
            user=self.user_a,
            change_description='Rev B',
        )
        # template is now is_current_version=False
        with self.assertRaises(ValueError) as ctx:
            create_new_milestone_template_version(
                self.template,
                user=self.user_a,
                change_description='Rev C from stale v1',
            )
        self.assertIn('current version', str(ctx.exception).lower())


class MilestoneCopyTestCase(TenantTestCase):
    """Milestone child rows are copied to the new template version; v1 rows stay intact."""

    def setUp(self):
        super().setUp()
        self.template = _make_template(name='MT-Copy Test Template')
        self.m1 = _add_milestone(self.template, 'MT-Quote Received', display_order=10,
                                  customer_display_name='Quote', is_active=True)
        self.m2 = _add_milestone(self.template, 'MT-PO Received', display_order=20,
                                  customer_display_name='PO', is_active=True)
        self.m3 = _add_milestone(self.template, 'MT-Closed', display_order=30,
                                  customer_display_name='Closed', is_active=False)

    def test_milestones_copied_to_new_version(self):
        v2 = create_new_milestone_template_version(
            self.template,
            user=self.user_a,
            change_description='Rev B — restructure milestones',
        )
        v2_milestones = list(v2.milestones.order_by('display_order'))
        self.assertEqual(len(v2_milestones), 3)
        # All must FK to v2
        for m in v2_milestones:
            self.assertEqual(m.template_id, v2.pk)

    def test_milestone_display_order_preserved(self):
        v2 = create_new_milestone_template_version(
            self.template,
            user=self.user_a,
            change_description='Rev B — display order check',
        )
        v2_orders = list(v2.milestones.order_by('display_order').values_list('display_order', flat=True))
        self.assertEqual(v2_orders, [10, 20, 30])

    def test_milestone_is_active_flag_preserved(self):
        v2 = create_new_milestone_template_version(
            self.template,
            user=self.user_a,
            change_description='Rev B — is_active check',
        )
        v2_milestones = {m.display_order: m for m in v2.milestones.all()}
        self.assertTrue(v2_milestones[10].is_active)
        self.assertTrue(v2_milestones[20].is_active)
        self.assertFalse(v2_milestones[30].is_active)

    def test_old_template_retains_its_milestones(self):
        """v1's Milestone rows must not be moved or deleted during versioning."""
        original_count = self.template.milestones.count()

        create_new_milestone_template_version(
            self.template,
            user=self.user_a,
            change_description='Rev B',
        )

        self.template.refresh_from_db()
        self.assertEqual(self.template.milestones.count(), original_count)
        # v1's primary keys must be unchanged
        v1_pks = set(self.template.milestones.values_list('pk', flat=True))
        self.assertIn(self.m1.pk, v1_pks)
        self.assertIn(self.m2.pk, v1_pks)
        self.assertIn(self.m3.pk, v1_pks)


class OrdersPinningTestCase(TenantTestCase):
    """
    Orders.current_milestone must stay pinned to v1's Milestone after
    template versioning. See module docstring for the full rationale.
    """

    def setUp(self):
        super().setUp()
        self.template = _make_template(name='MT-Pinning Test Template')
        self.m1 = _add_milestone(self.template, 'MT-Pin Quote', display_order=10, is_active=True)
        self.m2 = _add_milestone(self.template, 'MT-Pin PO', display_order=20, is_active=True)

        self.order = Orders.objects.create(
            name='MT-Pinning Test Order',
            current_milestone=self.m1,
        )

    def test_order_current_milestone_stays_with_v1_after_template_versioning(self):
        """
        After versioning, the Order's current_milestone FK must still resolve
        to the v1 Milestone row, not any row on v2.
        """
        v2 = create_new_milestone_template_version(
            self.template,
            user=self.user_a,
            change_description='Rev B — add new gate',
        )

        self.order.refresh_from_db()

        # Order still points at the original v1 Milestone
        self.assertEqual(self.order.current_milestone_id, self.m1.pk)
        self.assertEqual(self.order.current_milestone.template_id, self.template.pk)

        # Sanity: v2 has its own (different) Milestone PKs
        v2_pks = set(v2.milestones.values_list('pk', flat=True))
        self.assertNotIn(self.order.current_milestone_id, v2_pks)


class RevisionSignalTestCase(TenantTestCase):
    """`revision_created` fires on successful versioning with correct kwargs."""

    def setUp(self):
        super().setUp()
        self.template = _make_template(name='MT-Signal Test Template')
        self.received = MagicMock()
        revision_created.connect(self.received, sender=MilestoneTemplate)

    def tearDown(self):
        revision_created.disconnect(self.received, sender=MilestoneTemplate)
        super().tearDown()

    def test_signal_fires_with_expected_kwargs(self):
        v2 = create_new_milestone_template_version(
            self.template,
            user=self.user_a,
            change_description='Signal check',
        )
        self.received.assert_called_once()
        kwargs = self.received.call_args.kwargs
        self.assertEqual(kwargs['sender'], MilestoneTemplate)
        self.assertEqual(kwargs['old_version'].pk, self.template.pk)
        self.assertEqual(kwargs['new_version'].pk, v2.pk)
        self.assertEqual(kwargs['user'], self.user_a)
        self.assertEqual(kwargs['change_description'], 'Signal check')


class UniqueConstraintPartialTestCase(TenantTestCase):
    """Partial UniqueConstraint allows the same name across versions."""

    def test_same_name_allowed_for_historical_version(self):
        """After versioning, v1 (is_current_version=False) and v2 share the
        same tenant+name — the partial constraint must not reject v2's insert."""
        template = _make_template(name='MT-Partial Constraint Template')

        # Should not raise IntegrityError — v1 flips is_current_version=False
        # before v2 is inserted.
        v2 = create_new_milestone_template_version(
            template,
            user=self.user_a,
            change_description='Constraint test',
        )

        self.assertEqual(v2.name, template.name)
        self.assertTrue(v2.is_current_version)
        template.refresh_from_db()
        self.assertFalse(template.is_current_version)
