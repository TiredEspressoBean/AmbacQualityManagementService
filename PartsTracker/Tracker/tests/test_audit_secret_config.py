"""
Security-audit regression for crypto-secret configuration.

Previously SECRET_KEY and FIELD_ENCRYPTION_KEY fell back to hardcoded, repo-
committed values whenever DEBUG was truthy. A stray DEBUG=true on a real
deployment (esp. on-prem) would silently boot with publicly-known keys →
forgeable password-reset tokens + decryptable tenant secrets.

The fix removes the committed keys entirely and decouples "real deployment"
from DEBUG: on a real deployment a missing key FAILS CLOSED; only a local-dev
machine gets an ephemeral generated key.
"""

from django.conf import settings
from django.test import SimpleTestCase

from PartsTrackerApp.settings import _resolve_secret

# The hardcoded values that used to ship in source.
_OLD_DEV_SECRET_KEY = "dev-secret-key-DO-NOT-USE-IN-PRODUCTION"
_OLD_DEV_FERNET_KEY = "YJL3Y7Fvwl0qAOhVwVNlUlYahNcKrQIr6_P-VEMyrpE="


class ResolveSecretTests(SimpleTestCase):
    def test_env_value_always_wins(self):
        self.assertEqual(
            _resolve_secret("from-env", name="X", is_real_deployment=True,
                            dev_factory=lambda: "dev"),
            "from-env",
        )

    def test_real_deployment_missing_secret_fails_closed(self):
        with self.assertRaises(ValueError):
            _resolve_secret("", name="DJANGO_SECRET_KEY", is_real_deployment=True,
                            dev_factory=lambda: "dev")
        with self.assertRaises(ValueError):
            _resolve_secret(None, name="FIELD_ENCRYPTION_KEY", is_real_deployment=True,
                            dev_factory=lambda: "dev")

    def test_local_dev_missing_secret_generates_ephemeral(self):
        out = _resolve_secret(None, name="X", is_real_deployment=False,
                              dev_factory=lambda: "EPHEMERAL")
        self.assertEqual(out, "EPHEMERAL")


class NoCommittedKeysTests(SimpleTestCase):
    def test_committed_dev_keys_are_not_in_use(self):
        self.assertNotEqual(settings.SECRET_KEY, _OLD_DEV_SECRET_KEY)
        self.assertNotEqual(settings.FIELD_ENCRYPTION_KEY, _OLD_DEV_FERNET_KEY)

    def test_keys_present(self):
        self.assertTrue(settings.SECRET_KEY)
        self.assertTrue(settings.FIELD_ENCRYPTION_KEY)

    def test_committed_strings_absent_from_settings_source(self):
        # Defense against re-introduction: the literal keys must not reappear.
        import PartsTrackerApp.settings as s
        source = open(s.__file__, encoding="utf-8").read()
        self.assertNotIn(_OLD_DEV_SECRET_KEY, source)
        self.assertNotIn(_OLD_DEV_FERNET_KEY, source)
