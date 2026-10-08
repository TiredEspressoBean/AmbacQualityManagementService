"""A tenant group may not hold Django's own admin permissions.

Django's `admin` app registers add/change/delete/view_logentry — the same four
codenames django-auditlog registers, and the only ambiguous codenames in the system.
A preset naming `view_logentry` means the auditlog one, because that is what
`/api/auditlog/` enforces, but `Permission.objects.filter(codename__in=[...])` matches
both. Ten tenant groups ended up holding `admin.view_logentry`, Operator among them.

Permission checks read codename strings, so the extra grant changed no answer. It just
put tenant roles in another app's permission space — the kind of thing a permission
review flags and nobody can account for.
"""
from django.contrib.auth.models import Permission
from django.test import TestCase

from Tracker.presets import grantable_permissions


class GrantablePermissionsTests(TestCase):
    def test_admin_permissions_are_never_grantable(self):
        got = grantable_permissions().filter(content_type__app_label="admin")
        self.assertFalse(got.exists(), f"admin perms leaked into grantable: {list(got)}")

    def test_view_logentry_resolves_to_auditlog_not_admin(self):
        """The regression: this codename exists twice and the auditlog one is meant."""
        got = list(grantable_permissions(["view_logentry"]))
        self.assertEqual(len(got), 1, f"expected exactly one, got {got}")
        self.assertEqual(got[0].content_type.app_label, "auditlog")

    def test_all_four_logentry_codenames_are_disambiguated(self):
        for codename in ("add_logentry", "change_logentry",
                         "delete_logentry", "view_logentry"):
            with self.subTest(codename=codename):
                # Both rows exist — otherwise this test proves nothing.
                self.assertEqual(
                    Permission.objects.filter(codename=codename).count(), 2,
                    "expected admin + auditlog rows; the collision may have moved")
                got = list(grantable_permissions([codename]))
                self.assertEqual(len(got), 1)
                self.assertEqual(got[0].content_type.app_label, "auditlog")

    def test_an_unambiguous_codename_is_unaffected(self):
        got = list(grantable_permissions(["view_parts"]))
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].codename, "view_parts")

    def test_no_codenames_means_everything_grantable(self):
        """The `__all__` presets: every permission a tenant may hold, not every row."""
        everything = Permission.objects.count()
        grantable = grantable_permissions().count()
        self.assertLess(grantable, everything, "admin perms should be held back")
        self.assertEqual(
            everything - grantable,
            Permission.objects.filter(content_type__app_label="admin").count())

    def test_an_unknown_codename_yields_nothing_rather_than_raising(self):
        self.assertEqual(list(grantable_permissions(["no_such_permission"])), [])

    def test_presets_do_not_name_a_permission_only_the_admin_app_has(self):
        """If a preset ever needs an admin-only codename, this fails rather than
        silently granting nothing — the exclusion would otherwise swallow it."""
        from Tracker.presets import get_all_preset_permissions

        named = get_all_preset_permissions()
        admin_only = set(
            Permission.objects.filter(content_type__app_label="admin")
            .values_list("codename", flat=True)
        ) - set(
            Permission.objects.exclude(content_type__app_label="admin")
            .values_list("codename", flat=True)
        )
        self.assertEqual(named & admin_only, set())
