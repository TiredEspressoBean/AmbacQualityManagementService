"""
Security-audit regression for CORS / CSRF trusted-origin configuration.

The deployment previously trusted the entire shared `*.railway.app` PaaS
namespace via a CORS origin regex (and `https://*.railway.app` in
CSRF_TRUSTED_ORIGINS) while `CORS_ALLOW_CREDENTIALS=True` — so any stranger's
railway.app app could make credentialed cross-origin requests with a victim's
session cookie. Trust must be scoped to our own domains / explicit hosts.

A wildcard over a domain we control (e.g. `*.uqmes.com`) is fine; a wildcard
over the shared `railway.app` namespace is not — these tests target the latter.
"""

import re

from django.conf import settings
from django.test import SimpleTestCase

# Hosts on the shared PaaS namespace that an attacker could deploy.
_STRANGER_ORIGINS = [
    "https://evil.railway.app",
    "https://evil.up.railway.app",
    "https://attacker-frontend-production.up.railway.app",
]


class CorsConfigTests(SimpleTestCase):
    def test_credentials_enabled(self):
        # Documents the posture the wildcard ban protects: with credentialed
        # CORS, a too-broad allowlist directly exposes session cookies.
        self.assertTrue(getattr(settings, "CORS_ALLOW_CREDENTIALS", False))

    def test_no_origin_regex_matches_shared_paas_namespace(self):
        for pattern in getattr(settings, "CORS_ALLOWED_ORIGIN_REGEXES", []):
            compiled = re.compile(pattern)
            for origin in _STRANGER_ORIGINS:
                self.assertIsNone(
                    compiled.match(origin),
                    f"CORS regex {pattern!r} trusts shared-namespace origin {origin}",
                )

    def test_stranger_paas_origin_not_explicitly_listed(self):
        listed = set(getattr(settings, "CORS_ALLOWED_ORIGINS", []))
        for origin in _STRANGER_ORIGINS:
            self.assertNotIn(origin, listed)

    def test_no_railway_wildcard_in_csrf_trusted_origins(self):
        for origin in settings.CSRF_TRUSTED_ORIGINS:
            self.assertNotRegex(
                origin, r"\*\.(up\.)?railway\.app",
                f"CSRF trusts the shared railway.app namespace via {origin!r}",
            )

    def test_localhost_dev_origins_present(self):
        self.assertIn("http://localhost:5173", settings.CORS_ALLOWED_ORIGINS)
