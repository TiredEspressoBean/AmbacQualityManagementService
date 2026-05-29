"""
Tests for the permission service and declarative permission structure.
"""

from django.test import TestCase
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from Tracker.permissions import GROUPS, get_group_names, get_group_description, validate_structure
from Tracker.services.permission_service import PermissionService, apply_permissions, get_permission_diff
from Tracker.models import User, PermissionChangeLog


class PermissionStructureTests(TestCase):
    """Tests for the declarative permission structure."""

    def test_groups_defined(self):
        """All expected groups are defined."""
        expected_groups = [
            'Admin', 'QA_Manager', 'QA_Inspector',
            'Production_Manager', 'Production_Operator',
            'Document_Controller', 'Customer'
        ]
        for group in expected_groups:
            self.assertIn(group, GROUPS)

    def test_get_group_names(self):
        """get_group_names returns all group names."""
        names = get_group_names()
        self.assertEqual(len(names), 9)
        self.assertIn('Admin', names)
        self.assertIn('Customer', names)

    def test_get_group_description(self):
        """get_group_description returns description."""
        desc = get_group_description('Admin')
        self.assertIn('Full system access', desc)

    def test_admin_has_all_permissions(self):
        """Admin group has '__all__' permissions."""
        self.assertEqual(GROUPS['Admin']['permissions'], '__all__')

    def test_customer_has_limited_permissions(self):
        """Customer group has limited view permissions."""
        perms = GROUPS['Customer']['permissions']
        self.assertIn('Tracker.view_orders', perms)
        self.assertNotIn('Tracker.add_orders', perms)
        self.assertNotIn('Tracker.delete_orders', perms)

    def test_validate_structure_passes(self):
        """validate_structure returns no errors for valid structure."""
        issues = validate_structure()
        self.assertEqual(issues, [])

    def test_wildcard_patterns(self):
        """Wildcard patterns are defined correctly."""
        qa_inspector_perms = GROUPS['QA_Inspector']['permissions']
        # Should have view_* wildcard
        self.assertIn('Tracker.view_*', qa_inspector_perms)


class PermissionServiceTests(TestCase):
    """Tests for PermissionService."""

    def setUp(self):
        """Set up test user and service."""
        self.user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass'
        )
        self.service = PermissionService(user=self.user, source='test')

    def test_ensure_groups_exist(self):
        """ensure_groups_exist creates all groups."""
        # Clear any existing groups first
        Group.objects.all().delete()

        created = self.service.ensure_groups_exist()

        self.assertEqual(len(created), 9)
        self.assertTrue(Group.objects.filter(name='Admin').exists())
        self.assertTrue(Group.objects.filter(name='Customer').exists())

    def test_ensure_groups_exist_idempotent(self):
        """ensure_groups_exist is idempotent."""
        self.service.ensure_groups_exist()
        created = self.service.ensure_groups_exist()

        # Should not create any new groups on second run
        self.assertEqual(len(created), 0)

    def test_apply_permissions(self):
        """apply_permissions assigns permissions to groups."""
        self.service.ensure_groups_exist()
        results = self.service.apply_permissions()

        self.assertGreater(results['groups_processed'], 0)
        self.assertEqual(results['errors'], [])

    def test_apply_permissions_dry_run(self):
        """apply_permissions dry_run doesn't change database."""
        self.service.ensure_groups_exist()

        # First apply normally
        self.service.apply_permissions()

        # Clear permissions
        for group in Group.objects.all():
            group.permissions.clear()

        # Dry run should show changes but not apply
        results = self.service.apply_permissions(dry_run=True)

        self.assertGreater(results['permissions_added'], 0)

        # Permissions should still be empty
        admin_group = Group.objects.get(name='Admin')
        self.assertEqual(admin_group.permissions.count(), 0)

    def test_get_group_status(self):
        """get_group_status returns correct status."""
        self.service.ensure_groups_exist()

        status = self.service.get_group_status('Admin')

        self.assertEqual(status['group_name'], 'Admin')
        self.assertIn('description', status)
        self.assertIn('declared_permissions', status)
        self.assertIn('actual_permissions', status)
        self.assertIn('in_sync', status)

    def test_diff_detects_missing_permissions(self):
        """diff detects missing permissions."""
        self.service.ensure_groups_exist()

        # Clear all permissions from groups first
        for group in Group.objects.all():
            group.permissions.clear()

        # Reset the cached permissions
        self.service._all_tracker_permissions = None

        # Now groups have no permissions
        diffs = self.service.diff()

        # Should show permissions to add
        self.assertGreater(len(diffs), 0)
        self.assertIn('Admin', diffs)
        self.assertGreater(len(diffs['Admin']['to_add']), 0)

    def test_diff_after_apply(self):
        """diff returns empty after apply_permissions."""
        self.service.ensure_groups_exist()
        self.service.apply_permissions()

        diffs = self.service.diff()

        # Should be in sync now
        self.assertEqual(diffs, {})


class PermissionChangeLogTests(TestCase):
    """Tests for permission change logging."""

    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass'
        )

    def test_changes_are_logged(self):
        """Permission changes are logged to PermissionChangeLog."""
        service = PermissionService(user=self.user, source='test_logged')
        service.ensure_groups_exist()

        # Record count before
        initial_count = PermissionChangeLog.objects.filter(source='test_logged').count()

        # Clear all permissions from groups so there's something to apply
        for group in Group.objects.all():
            group.permissions.clear()

        # Reset cached permissions
        service._all_tracker_permissions = None

        service.apply_permissions()

        # Should have logged more changes
        final_count = PermissionChangeLog.objects.filter(source='test_logged').count()
        self.assertGreater(final_count, initial_count)

    def test_log_contains_correct_info(self):
        """Log entries contain correct information."""
        unique_source = 'test_info_check'
        service = PermissionService(user=self.user, source=unique_source)
        service.ensure_groups_exist()

        # Clear all permissions from groups so there's something to apply
        for group in Group.objects.all():
            group.permissions.clear()

        # Reset cached permissions
        service._all_tracker_permissions = None

        service.apply_permissions()

        # Get logs with our unique source
        log = PermissionChangeLog.objects.filter(source=unique_source).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.source, unique_source)
        self.assertEqual(log.action, 'added')
        self.assertIsNotNone(log.group_name)
        self.assertIsNotNone(log.permission_codename)


class ConvenienceFunctionTests(TestCase):
    """Tests for convenience functions."""

    def test_apply_permissions_function(self):
        """apply_permissions convenience function works."""
        results = apply_permissions(source='test')

        self.assertIn('groups_processed', results)
        self.assertIn('permissions_added', results)
        self.assertIn('errors', results)

    def test_get_permission_diff_function(self):
        """get_permission_diff convenience function works."""
        apply_permissions(source='test')
        diffs = get_permission_diff()

        # Should be a dict (possibly empty if in sync)
        self.assertIsInstance(diffs, dict)


class PermissionIntegrityTests(TestCase):
    """Tests for database permission integrity - catches common issues."""

    def test_no_duplicate_permissions(self):
        """No duplicate permissions exist (same app_label + codename)."""
        from django.db.models import Count

        duplicates = (
            Permission.objects
            .values('content_type__app_label', 'codename')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        duplicate_list = list(duplicates)
        if duplicate_list:
            details = []
            for d in duplicate_list:
                perms = Permission.objects.filter(
                    content_type__app_label=d['content_type__app_label'],
                    codename=d['codename']
                ).select_related('content_type')
                for p in perms:
                    details.append(
                        f"  {p.id}: {p.content_type.app_label}.{p.codename} "
                        f"(content_type={p.content_type}, ct_id={p.content_type_id})"
                    )

            self.fail(
                f"Found {len(duplicate_list)} duplicate permission(s):\n"
                + "\n".join(details)
            )

    def test_no_orphaned_content_types(self):
        """No content types exist for models that no longer exist."""
        orphaned = []
        for ct in ContentType.objects.filter(app_label='Tracker'):
            model_class = ct.model_class()
            if model_class is None:
                orphaned.append(f"{ct.app_label}.{ct.model} (id={ct.id})")

        if orphaned:
            self.fail(
                f"Found {len(orphaned)} orphaned content type(s) - "
                f"these should be cleaned up:\n  " + "\n  ".join(orphaned)
            )

    def test_declared_permissions_exist(self):
        """All permissions declared in permissions.py exist in database."""
        from Tracker.permissions import MODULE_PERMISSIONS, MODULE_APPS

        missing = []
        for module, config in MODULE_PERMISSIONS.items():
            app_label = MODULE_APPS.get(module, 'Tracker')
            for codename in config.get('models', []):
                exists = Permission.objects.filter(
                    content_type__app_label=app_label,
                    codename=codename
                ).exists()
                if not exists:
                    missing.append(f"{app_label}.{codename}")

        if missing:
            self.fail(
                f"Found {len(missing)} declared permission(s) that don't exist "
                f"in database (may need migration):\n  " + "\n  ".join(missing)
            )

    def test_custom_permissions_have_content_type(self):
        """Custom permissions are attached to correct content types."""
        # Map of custom permission -> expected model
        custom_permission_models = {
            'approve_qualityreports': 'qualityreports',
            'approve_own_qualityreports': 'qualityreports',
            'approve_disposition': 'quarantinedisposition',
            'close_disposition': 'quarantinedisposition',
            'initiate_capa': 'capa',
            'close_capa': 'capa',
            'approve_capa': 'capa',
            'verify_capa': 'capa',
            'conduct_rca': 'rcarecord',
            'review_rca': 'rcarecord',
            'respond_to_approval': 'approvalrequest',
            'create_approval_template': 'approvaltemplate',
            'manage_approval_workflow': 'approvaltemplate',
            'view_confidential_documents': 'documents',
            'view_restricted_documents': 'documents',
            'view_secret_documents': 'documents',
            'classify_documents': 'documents',
        }

        issues = []
        for codename, expected_model in custom_permission_models.items():
            perms = Permission.objects.filter(
                content_type__app_label='Tracker',
                codename=codename
            ).select_related('content_type')

            if perms.count() == 0:
                issues.append(f"{codename}: NOT FOUND")
            elif perms.count() > 1:
                models = [p.content_type.model for p in perms]
                issues.append(f"{codename}: DUPLICATE on {models}")
            else:
                perm = perms.first()
                if perm.content_type.model != expected_model:
                    issues.append(
                        f"{codename}: wrong model - expected {expected_model}, "
                        f"got {perm.content_type.model}"
                    )

        if issues:
            self.fail(
                f"Found {len(issues)} custom permission issue(s):\n  "
                + "\n  ".join(issues)
            )


class TenantModelPermissionsActionGateTests(TestCase):
    """
    Tests for the action_permissions branch added to TenantModelPermissions.

    The class now checks an optional `action_permissions` dict on the viewset
    after the CRUD perm passes. Viewsets without the attribute behave exactly
    as before; actions not listed in the dict fall through to CRUD-only.
    """

    def setUp(self):
        from rest_framework.test import APIRequestFactory
        from Tracker.permissions import TenantModelPermissions
        from Tracker.models import Tenant
        from Tracker.utils.tenant_context import set_current_tenant_id

        self.factory = APIRequestFactory()
        self.perm_class = TenantModelPermissions()

        self.tenant = Tenant.objects.create(name="T", slug="t", tier="PRO")
        self._tok = set_current_tenant_id(self.tenant.id)

        # Build a user who has the CRUD perm we'll exercise but neither
        # of the action-specific perms. Each test grants what it needs on
        # top of this baseline via assign_perms().
        self.user = User.objects.create_user(
            username='u', email='u@t.com', password='x', tenant=self.tenant,
        )

    def tearDown(self):
        from Tracker.utils.tenant_context import reset_current_tenant
        reset_current_tenant(self._tok)

    def _assign_perms(self, *codenames):
        """Grant tenant-scoped perms to self.user via a tenant group."""
        from django.contrib.auth.models import Permission
        from Tracker.models import TenantGroup

        group = TenantGroup.objects.create(
            tenant=self.tenant, name=f"grp-{'-'.join(codenames) or 'empty'}",
        )
        for codename in codenames:
            perm = Permission.objects.filter(codename=codename).first()
            if perm:
                group.permissions.add(perm)
        self.user.add_to_tenant_group(group, tenant=self.tenant)
        self.user.clear_permission_cache(self.tenant)

    def _make_view(self, *, model_class, action_name, action_permissions=None):
        """Build a minimal stand-in for a DRF viewset."""
        class _StubView:
            queryset = type('Q', (), {'model': model_class})()
            action = action_name
        if action_permissions is not None:
            _StubView.action_permissions = action_permissions
        return _StubView()

    def _make_request(self, method='POST'):
        request = getattr(self.factory, method.lower())('/x/')
        request.user = self.user
        return request

    def test_no_action_permissions_attr_behaves_unchanged(self):
        """Viewsets without action_permissions get the legacy CRUD-only check."""
        from Tracker.models import RcaRecord
        view = self._make_view(model_class=RcaRecord, action_name='approve_rca')

        # User lacks add_rcarecord — should be rejected by the CRUD gate.
        self.assertFalse(self.perm_class.has_permission(self._make_request(), view))

        # Grant add_rcarecord; with no action_permissions, this is sufficient.
        self._assign_perms('add_rcarecord')
        self.assertTrue(self.perm_class.has_permission(self._make_request(), view))

    def test_action_perm_required_user_lacks_it_rejected(self):
        """User with CRUD perm but missing action perm is rejected."""
        from Tracker.models import RcaRecord
        self._assign_perms('add_rcarecord')  # CRUD passes, action does not.
        view = self._make_view(
            model_class=RcaRecord,
            action_name='approve_rca',
            action_permissions={'approve_rca': ['review_rca']},
        )
        self.assertFalse(self.perm_class.has_permission(self._make_request(), view))

    def test_action_perm_required_user_has_it_passes(self):
        """User with both CRUD and action perms passes."""
        from Tracker.models import RcaRecord
        self._assign_perms('add_rcarecord', 'review_rca')
        view = self._make_view(
            model_class=RcaRecord,
            action_name='approve_rca',
            action_permissions={'approve_rca': ['review_rca']},
        )
        self.assertTrue(self.perm_class.has_permission(self._make_request(), view))

    def test_action_not_in_dict_falls_through_to_crud_only(self):
        """Action absent from action_permissions only requires the CRUD perm."""
        from Tracker.models import RcaRecord
        self._assign_perms('add_rcarecord')  # CRUD passes, no action perm needed.
        view = self._make_view(
            model_class=RcaRecord,
            action_name='submit_for_review',  # not in dict below
            action_permissions={'approve_rca': ['review_rca']},
        )
        self.assertTrue(self.perm_class.has_permission(self._make_request(), view))

    def test_multiple_action_perms_all_required(self):
        """When action_permissions lists N perms, the user needs ALL of them."""
        from Tracker.models import RcaRecord
        view = self._make_view(
            model_class=RcaRecord,
            action_name='approve_rca',
            action_permissions={'approve_rca': ['review_rca', 'conduct_rca']},
        )

        # CRUD + one of two action perms — still rejected.
        self._assign_perms('add_rcarecord', 'review_rca')
        self.assertFalse(self.perm_class.has_permission(self._make_request(), view))

    def test_crud_perm_failure_short_circuits_action_check(self):
        """If the CRUD gate rejects, action_permissions are not consulted."""
        from Tracker.models import RcaRecord
        # User has the action perm but lacks the CRUD perm.
        self._assign_perms('review_rca')  # no add_rcarecord
        view = self._make_view(
            model_class=RcaRecord,
            action_name='approve_rca',
            action_permissions={'approve_rca': ['review_rca']},
        )
        self.assertFalse(self.perm_class.has_permission(self._make_request(), view))
