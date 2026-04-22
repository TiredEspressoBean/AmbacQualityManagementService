"""
Tests for `SecureModel.create_new_version` and `get_version_history`.

Exercised through `DocumentType` because it's the simplest leaf
versioned SecureModel and its serializer already routes content edits
through `create_new_version` (closing the DMS "silent toggle" gap).

Covers:
  - Happy path: field copy + increment + previous_version link
  - Exclusion list: excluded fields are NOT copied forward
  - Tenant preservation across versions
  - Archived guard (can't version a soft-deleted row)
  - Current-version guard (can't version a historical row)
  - Concurrent-call safety via SELECT FOR UPDATE
  - Cycle protection in get_version_history
  - Serializer routing (content edit → version; archive-only → save)
"""
from unittest.mock import patch

from django.test import TransactionTestCase
from rest_framework.test import APIRequestFactory

from Tracker.models import DocumentType, Tenant
from Tracker.serializers.dms import DocumentTypeSerializer
from Tracker.tests.base import TenantTestCase
from Tracker.utils.tenant_context import set_current_tenant_id, reset_current_tenant


class SecureModelVersioningTestCase(TenantTestCase):
    """Base `create_new_version` mechanics."""

    def setUp(self):
        super().setUp()
        # Unique code/name — SOP/WI/DWG/etc. are in the default-seed set.
        self.dt = DocumentType.objects.create(
            name='TestBase Procedure',
            code='ZZBASE',
            description='Initial test type',
            requires_approval=True,
            default_review_period_days=365,
            default_retention_days=2555,
        )

    def test_basic_versioning_increments_version_and_links_parent(self):
        v2 = self.dt.create_new_version(description='Updated description')

        self.assertEqual(v2.version, 2)
        self.assertEqual(v2.previous_version, self.dt)
        self.assertTrue(v2.is_current_version)
        self.assertEqual(v2.description, 'Updated description')

        # Parent is marked historical.
        self.dt.refresh_from_db()
        self.assertFalse(self.dt.is_current_version)
        self.assertEqual(self.dt.version, 1)

    def test_unchanged_fields_are_carried_forward(self):
        v2 = self.dt.create_new_version(description='Rev B')

        # Every field not in the update kwargs and not in the exclusion
        # list should equal the parent's value.
        self.assertEqual(v2.name, self.dt.name)
        self.assertEqual(v2.code, self.dt.code)
        self.assertEqual(v2.requires_approval, self.dt.requires_approval)
        self.assertEqual(v2.default_review_period_days, self.dt.default_review_period_days)
        self.assertEqual(v2.default_retention_days, self.dt.default_retention_days)

    def test_excluded_fields_are_not_carried_forward(self):
        # Dirty the parent's soft-delete state then version it.
        # We can't set archived=True directly (the guard would block)
        # so we simulate a non-archived parent whose new version should
        # still start with archived=False even if _VERSIONING_EXCLUDE_FIELDS
        # skips it on copy.
        v2 = self.dt.create_new_version(description='Rev')

        # id, created_at, version, previous_version, is_current_version,
        # archived, deleted_at are all excluded. Verify archived defaults
        # rather than mirroring the parent.
        self.assertNotEqual(v2.id, self.dt.id)
        self.assertFalse(v2.archived)
        self.assertIsNone(v2.deleted_at)

    def test_tenant_is_preserved_across_versions(self):
        v2 = self.dt.create_new_version(description='Rev')
        # Normalize types — both sides may be UUID instances or strings
        # depending on how they were set at save time.
        self.assertEqual(str(v2.tenant_id), str(self.dt.tenant_id))
        self.assertEqual(str(v2.tenant_id), str(self.tenant_a.id))

    def test_archived_record_cannot_be_versioned(self):
        self.dt.archived = True
        self.dt.save(update_fields=['archived'])

        with self.assertRaises(ValueError) as ctx:
            self.dt.create_new_version(description='Rev')
        self.assertIn('archived', str(ctx.exception).lower())

    def test_non_current_version_cannot_be_versioned(self):
        v2 = self.dt.create_new_version(description='Rev B')
        self.dt.refresh_from_db()

        # self.dt is now historical (v1). Versioning it should fail.
        with self.assertRaises(ValueError) as ctx:
            self.dt.create_new_version(description='Rev C from v1')
        self.assertIn('current version', str(ctx.exception).lower())

    def test_explicit_updates_override_copied_fields(self):
        v2 = self.dt.create_new_version(
            description='Rev B',
            requires_approval=False,
        )

        self.assertEqual(v2.description, 'Rev B')
        self.assertFalse(v2.requires_approval)
        # Untouched field still carried forward.
        self.assertEqual(v2.code, 'ZZBASE')

    def test_chained_versions_preserve_ancestry(self):
        v2 = self.dt.create_new_version(description='Rev B')
        v3 = v2.create_new_version(description='Rev C')

        self.assertEqual(v3.version, 3)
        self.assertEqual(v3.previous_version, v2)
        self.assertEqual(v2.previous_version, self.dt)

        v2.refresh_from_db()
        self.assertFalse(v2.is_current_version)
        self.assertTrue(v3.is_current_version)


class VersionHistoryTestCase(TenantTestCase):
    """`get_version_history` returns full chain; is cycle-safe."""

    def setUp(self):
        super().setUp()
        self.v1 = DocumentType.objects.create(
            name='TestHistory Instruction', code='ZZHIST', description='v1',
        )
        self.v2 = self.v1.create_new_version(description='v2')
        self.v3 = self.v2.create_new_version(description='v3')

    def test_history_is_ordered_oldest_first(self):
        history = self.v3.get_version_history()
        self.assertEqual([v.version for v in history], [1, 2, 3])

    def test_history_from_any_version_returns_full_chain(self):
        # Walking from v1 or v2 or v3 should all yield the same chain.
        self.assertEqual(len(self.v1.get_version_history()), 3)
        self.assertEqual(len(self.v2.get_version_history()), 3)
        self.assertEqual(len(self.v3.get_version_history()), 3)

    def test_cycle_in_previous_version_does_not_hang(self):
        # Forge a cycle: v1.previous_version = v3. This is a data-
        # corruption scenario, not a normal flow.
        DocumentType.all_tenants.filter(pk=self.v1.pk).update(previous_version=self.v3)
        self.v1.refresh_from_db()

        # Must terminate. Content correctness isn't the claim here;
        # the claim is "doesn't infinite-loop."
        history = self.v3.get_version_history()
        self.assertIsInstance(history, list)
        self.assertLessEqual(len(history), 10)  # generous upper bound


class DocumentTypeSerializerRoutingTestCase(TenantTestCase):
    """`DocumentTypeSerializer.update` routes content edits through
    versioning; archive toggles through plain save."""

    def setUp(self):
        super().setUp()
        # Unique name/code — `DWG` and other common codes are in the
        # default-seed set created on tenant setUp.
        self.dt = DocumentType.objects.create(
            name='TestRouting Drawing', code='ZZROUTE', description='v1',
        )
        self.factory = APIRequestFactory()

    def _serializer(self, instance, data, partial=True):
        request = self.factory.patch('/')
        request.user = self.user_a
        return DocumentTypeSerializer(
            instance, data=data, partial=partial,
            context={'request': request},
        )

    def test_content_edit_creates_new_version(self):
        s = self._serializer(self.dt, {'description': 'Rev B'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.description, 'Rev B')
        self.dt.refresh_from_db()
        self.assertFalse(self.dt.is_current_version)

    def test_requires_approval_toggle_creates_new_version(self):
        """The specific DMS gap the versioning doc called out."""
        s = self._serializer(self.dt, {'requires_approval': False})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertFalse(result.requires_approval)

    def test_archive_only_update_does_not_version(self):
        s = self._serializer(self.dt, {'archived': True})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertTrue(result.archived)
        # Same id; same row.
        self.assertEqual(result.id, self.dt.id)

    def test_mixed_archive_and_content_creates_new_version(self):
        # If any content field is in the payload, route through versioning
        # even if archived is also present.
        s = self._serializer(self.dt, {'archived': True, 'description': 'Rev B'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.description, 'Rev B')

    def test_empty_update_is_noop(self):
        s = self._serializer(self.dt, {})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.pk, self.dt.pk)
        self.assertEqual(result.version, 1)


class ConcurrentVersioningTestCase(TransactionTestCase):
    """The `SELECT FOR UPDATE` lock prevents two concurrent callers
    from both observing is_current_version=True and both creating v2.

    `TransactionTestCase` (not TenantTestCase) because the test drives
    real transactions — wrapping ContextVar manually rather than via
    TenantTestCase.setUp.
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Concurrent Tenant', slug='concurrent-tenant', tier='PRO',
        )
        self._cv_token = set_current_tenant_id(self.tenant.id)
        # Unique name/code — new tenants auto-seed default DocumentTypes
        # including 'SOP' via defaults_service; collision risk otherwise.
        self.dt = DocumentType.objects.create(
            name='ConcTestDoc', code='CONCTEST', description='v1',
        )

    def tearDown(self):
        reset_current_tenant(self._cv_token)

    def test_lock_is_acquired_on_source_row(self):
        """Smoke-test that create_new_version uses SELECT FOR UPDATE.

        We patch the model manager's select_for_update to count calls.
        If the implementation isn't locking, the patch won't fire.
        """
        from Tracker.models import DocumentType as DT

        real_manager = DT.all_tenants
        call_count = {'n': 0}

        real_sfu = real_manager.select_for_update

        def counting_sfu(*args, **kwargs):
            call_count['n'] += 1
            return real_sfu(*args, **kwargs)

        with patch.object(real_manager, 'select_for_update', side_effect=counting_sfu):
            self.dt.create_new_version(description='v2')

        self.assertGreaterEqual(call_count['n'], 1)
