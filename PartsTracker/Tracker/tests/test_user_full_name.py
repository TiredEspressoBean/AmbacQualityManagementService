"""User.get_full_name() must return '' — not "None None" — for a nameless user.

This model declares `first_name`/`last_name` as `null=True`, where Django's
own AbstractUser fields are `blank=True` non-null. `AbstractUser.get_full_name`
builds the name with `"%s %s" % (self.first_name, self.last_name)`, so with
both fields NULL it produced the literal string "None None".

Because that string is truthy, the `get_full_name() or username` idiom used
across ~50 call sites never reached its fallback. It surfaced anywhere a
person is named — most visibly the customer- and auditor-facing report PDFs
(SCAR, NCR, CAPA report, calibration certificate, deviation request,
training record, SPC), which all do `full.strip() or email or username` and
were defeated identically, plus approval notification emails, the
`display_name` property, and several `__str__` methods.

Fixed on the accessor so the standard idiom is correct everywhere.
"""
from django.contrib.auth import get_user_model

from Tracker.models import Tenant
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class UserGetFullNameTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Name Test", slug="name-test", tier="PRO",
        )
        self.set_tenant_context(self.tenant)
        self.User = get_user_model()

    def _user(self, username, **kwargs):
        return self.User.objects.create_user(
            username=username, email=f"{username}@test.test", password="x",
            tenant=self.tenant, **kwargs,
        )

    def test_no_name_returns_empty_string_not_none_none(self):
        """The core bug."""
        u = self._user("nameless")
        self.assertEqual(u.get_full_name(), '')
        self.assertNotIn('None', u.get_full_name())

    def test_explicit_null_names_return_empty_string(self):
        u = self._user("nulled", first_name=None, last_name=None)
        self.assertEqual(u.get_full_name(), '')

    def test_the_or_username_idiom_now_reaches_its_fallback(self):
        """This is what ~50 call sites actually do."""
        u = self._user("fallback-me")
        self.assertEqual(u.get_full_name() or u.username, 'fallback-me')

    def test_report_adapter_idiom_now_reaches_its_fallback(self):
        """The report adapters do `full.strip() or email or username`."""
        u = self._user("pdf-user")
        full = u.get_full_name()
        self.assertEqual(full.strip() or u.email or u.username, 'pdf-user@test.test')

    def test_both_names_present(self):
        u = self._user("both", first_name="Dana", last_name="Reyes")
        self.assertEqual(u.get_full_name(), 'Dana Reyes')

    def test_first_name_only(self):
        u = self._user("firstonly", first_name="Dana")
        self.assertEqual(u.get_full_name(), 'Dana')

    def test_last_name_only(self):
        """Must not leave a leading space."""
        u = self._user("lastonly", last_name="Reyes")
        self.assertEqual(u.get_full_name(), 'Reyes')

    def test_display_name_falls_back_to_username(self):
        u = self._user("dn-user")
        self.assertEqual(u.display_name, 'dn-user')

    def test_display_name_uses_full_name_when_set(self):
        u = self._user("dn-named", first_name="Dana", last_name="Reyes")
        self.assertEqual(u.display_name, 'Dana Reyes')

    def test_get_short_name_returns_empty_string_not_none(self):
        u = self._user("shortless")
        self.assertEqual(u.get_short_name(), '')

    def test_get_short_name_returns_first_name(self):
        u = self._user("shorty", first_name="Dana")
        self.assertEqual(u.get_short_name(), 'Dana')
