"""
Tests for `ApprovalTemplate.create_new_version` (composite versioning).

Covers:
  - Basic versioning mechanics (version increment, previous_version link)
  - `change_description` required (compliance — ISO 9001 4.4)
  - Tenant preserved across versions
  - Archived record cannot be versioned
  - Field overrides forwarded to new version
  - M2M copy: default_approvers copied to new version
  - M2M copy: default_groups copied to new version
  - M2M through-rows are distinct (old rows point at v1, new rows at v2)
  - Modifying v2 approvers does not affect v1
  - `revision_created` signal emission
  - UniqueConstraint partial — multiple versions with same natural key coexist

Seed-collision note: TenantTestCase.setUp triggers `post_save(Tenant)` which
seeds six default ApprovalTemplates (DOCUMENT_RELEASE, CAPA_CRITICAL,
CAPA_MAJOR, ECO, TRAINING_CERT, PROCESS_APPROVAL) on each tenant. All
fixtures here use `approval_type='ZZTEST'` (not in the seeded set) and
`template_name` values prefixed with 'ZZ' to avoid uniqueness collisions.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from django.contrib.auth import get_user_model

from Tracker.models.core import ApprovalTemplate, TenantGroup
from Tracker.services.core.approval_template import create_new_approval_template_version
from Tracker.signals_versioning import revision_created
from Tracker.tests.base import TenantTestCase

User = get_user_model()


def _make_template(tenant, *, template_name='ZZ Test Template', approval_type='ZZTEST'):
    """Build a minimal ApprovalTemplate for versioning tests."""
    return ApprovalTemplate.objects.create(
        template_name=template_name,
        approval_type=approval_type,
        tenant=tenant,
    )


class CreateNewApprovalTemplateVersionTestCase(TenantTestCase):
    """Core versioning mechanics on ApprovalTemplate."""

    def setUp(self):
        super().setUp()
        self.template = _make_template(self.tenant_a)

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_creates_new_version_with_incremented_version(self):
        v2 = create_new_approval_template_version(
            self.template,
            user=self.user_a,
            change_description='Updated escalation policy',
        )
        self.assertEqual(v2.version, 2)
        self.assertEqual(v2.previous_version_id, self.template.pk)
        self.assertTrue(v2.is_current_version)

        self.template.refresh_from_db()
        self.assertFalse(self.template.is_current_version)

    def test_tenant_preserved(self):
        v2 = create_new_approval_template_version(
            self.template,
            user=self.user_a,
            change_description='Rev',
        )
        self.assertEqual(str(v2.tenant_id), str(self.template.tenant_id))
        self.assertEqual(str(v2.tenant_id), str(self.tenant_a.id))

    def test_field_overrides_applied_to_new_version(self):
        v2 = create_new_approval_template_version(
            self.template,
            user=self.user_a,
            change_description='Changed due days',
            default_due_days=10,
        )
        self.assertEqual(v2.default_due_days, 10)

    def test_archived_record_cannot_be_versioned(self):
        self.template.archived = True
        self.template.save(update_fields=['archived'])
        with self.assertRaises(ValueError):
            create_new_approval_template_version(
                self.template,
                user=self.user_a,
                change_description='Should fail',
            )

    # ------------------------------------------------------------------
    # Guard: change_description required
    # ------------------------------------------------------------------

    def test_blank_change_description_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            create_new_approval_template_version(
                self.template,
                user=self.user_a,
                change_description='',
            )
        self.assertIn('change_description', str(ctx.exception))

    def test_whitespace_only_change_description_rejected(self):
        with self.assertRaises(ValueError):
            create_new_approval_template_version(
                self.template,
                user=self.user_a,
                change_description='   ',
            )


class M2MChildCopyTestCase(TenantTestCase):
    """M2M through-row copy mechanics — the structural difference from FK-child composites."""

    def setUp(self):
        super().setUp()
        self.template = _make_template(self.tenant_a, template_name='ZZ M2M Template', approval_type='ZZTEST2')

        # Create additional users attached to the same tenant for approver assignments.
        self.approver_b = User.objects.create_user(
            username='approver_b',
            email='approver_b@tenant-a.com',
            password='testpass123',
            tenant=self.tenant_a,
        )
        self.approver_c = User.objects.create_user(
            username='approver_c',
            email='approver_c@tenant-a.com',
            password='testpass123',
            tenant=self.tenant_a,
        )

        self.group_x = TenantGroup.objects.create(
            tenant=self.tenant_a,
            name='ZZ Group X',
            description='Test group X',
            is_custom=True,
        )
        self.group_y = TenantGroup.objects.create(
            tenant=self.tenant_a,
            name='ZZ Group Y',
            description='Test group Y',
            is_custom=True,
        )

    def test_default_approvers_copied_to_new_version(self):
        self.template.default_approvers.set([self.user_a, self.approver_b])

        v2 = create_new_approval_template_version(
            self.template,
            user=self.user_a,
            change_description='Updating approvers',
        )

        v2_approver_ids = set(v2.default_approvers.values_list('id', flat=True))
        expected_ids = {self.user_a.pk, self.approver_b.pk}
        self.assertEqual(v2_approver_ids, expected_ids)

    def test_default_groups_copied_to_new_version(self):
        self.template.default_groups.set([self.group_x, self.group_y])

        v2 = create_new_approval_template_version(
            self.template,
            user=self.user_a,
            change_description='Updating groups',
        )

        v2_group_ids = set(v2.default_groups.values_list('id', flat=True))
        expected_ids = {self.group_x.pk, self.group_y.pk}
        self.assertEqual(v2_group_ids, expected_ids)

    def test_m2m_through_rows_are_distinct(self):
        """Old through rows point at v1, new through rows point at v2.

        Same User/Group on the other side — different through-table rows.
        Verifies historical pinning: v1's membership set is its own set of
        through-table rows distinct from v2's set.
        """
        self.template.default_approvers.set([self.user_a])
        self.template.default_groups.set([self.group_x])

        v1_approver_qs = self.template.default_approvers.through.objects.filter(
            approvaltemplate=self.template
        )
        v1_group_qs = self.template.default_groups.through.objects.filter(
            approvaltemplate=self.template
        )

        v2 = create_new_approval_template_version(
            self.template,
            user=self.user_a,
            change_description='Structural distinction test',
        )

        v2_approver_qs = v2.default_approvers.through.objects.filter(
            approvaltemplate=v2
        )
        v2_group_qs = v2.default_groups.through.objects.filter(
            approvaltemplate=v2
        )

        # v1 and v2 each own their own through-table rows.
        self.assertEqual(v1_approver_qs.count(), 1)
        self.assertEqual(v2_approver_qs.count(), 1)
        self.assertNotEqual(
            v1_approver_qs.first().pk,
            v2_approver_qs.first().pk,
        )

        self.assertEqual(v1_group_qs.count(), 1)
        self.assertEqual(v2_group_qs.count(), 1)
        self.assertNotEqual(
            v1_group_qs.first().pk,
            v2_group_qs.first().pk,
        )

    def test_modifying_v2_approvers_does_not_affect_v1(self):
        """Critical invariant: divergence after copy is isolated.

        v1 and v2 start with the same approver set. Adding approver_c to v2
        must not appear on v1.
        """
        self.template.default_approvers.set([self.user_a, self.approver_b])

        v2 = create_new_approval_template_version(
            self.template,
            user=self.user_a,
            change_description='Divergence test',
        )

        # Add a new approver to v2.
        v2.default_approvers.add(self.approver_c)

        v1_approver_ids = set(self.template.default_approvers.values_list('id', flat=True))
        v2_approver_ids = set(v2.default_approvers.values_list('id', flat=True))

        # v1 is unchanged.
        self.assertEqual(v1_approver_ids, {self.user_a.pk, self.approver_b.pk})
        # v2 now has three approvers.
        self.assertEqual(v2_approver_ids, {self.user_a.pk, self.approver_b.pk, self.approver_c.pk})


class RevisionSignalTestCase(TenantTestCase):
    """`revision_created` fires on successful ApprovalTemplate versioning."""

    def setUp(self):
        super().setUp()
        self.template = _make_template(
            self.tenant_a,
            template_name='ZZ Signal Template',
            approval_type='ZZTEST3',
        )
        self.received = MagicMock()
        revision_created.connect(self.received, sender=ApprovalTemplate)

    def tearDown(self):
        revision_created.disconnect(self.received, sender=ApprovalTemplate)
        super().tearDown()

    def test_revision_created_signal_fires_with_correct_kwargs(self):
        v2 = create_new_approval_template_version(
            self.template,
            user=self.user_a,
            change_description='Signal test — escalation policy update',
        )
        self.received.assert_called_once()
        kwargs = self.received.call_args.kwargs
        self.assertEqual(kwargs['sender'], ApprovalTemplate)
        self.assertEqual(kwargs['old_version'].pk, self.template.pk)
        self.assertEqual(kwargs['new_version'].pk, v2.pk)
        self.assertEqual(kwargs['user'], self.user_a)
        self.assertEqual(
            kwargs['change_description'],
            'Signal test — escalation policy update',
        )


class UniqueConstraintPartialTestCase(TenantTestCase):
    """Partial UniqueConstraint allows multiple versions of the same natural key."""

    def test_multiple_versions_with_same_natural_key_coexist(self):
        """Two rows with identical (tenant, template_name) and (tenant, approval_type)
        must coexist once the constraints are partial on is_current_version=True."""
        template_v1 = _make_template(
            self.tenant_a,
            template_name='ZZ Constraint Template',
            approval_type='ZZTEST4',
        )
        # This call previously would violate the unconditional unique
        # constraints; the partial constraints permit it.
        v2 = create_new_approval_template_version(
            template_v1,
            user=self.user_a,
            change_description='Constraint test rev',
        )
        self.assertEqual(v2.version, 2)

        # Both rows exist with the same natural key values.
        all_rows = list(
            ApprovalTemplate.all_tenants.filter(
                tenant=self.tenant_a,
                template_name='ZZ Constraint Template',
                approval_type='ZZTEST4',
            )
        )
        self.assertEqual(len(all_rows), 2)
        current_rows = [r for r in all_rows if r.is_current_version]
        self.assertEqual(len(current_rows), 1)
        self.assertEqual(current_rows[0].pk, v2.pk)
