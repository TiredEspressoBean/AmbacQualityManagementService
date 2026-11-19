"""Django's admin lives at /djangoadmin/: /admin/ is the app's own pages, which a new tab
or a refresh must open in the app, not Django's admin (prod bug 2026-11-19)."""
from django.test import SimpleTestCase
from django.urls import Resolver404, resolve, reverse


class DjangoAdminPathTests(SimpleTestCase):
    def test_the_django_admin_is_at_djangoadmin(self):
        self.assertEqual(reverse("admin:index"), "/djangoadmin/")
        self.assertEqual(resolve("/djangoadmin/").app_name, "admin")

    def test_admin_is_no_longer_a_django_route(self):
        for path in ("/admin/", "/admin/users", "/admin/doc/"):
            with self.assertRaises(Resolver404, msg=path):
                resolve(path)
