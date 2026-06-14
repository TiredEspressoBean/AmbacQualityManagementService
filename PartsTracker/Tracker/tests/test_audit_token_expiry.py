"""
Security-audit regression for API token expiry + rotation.

DRF's stock Token never expires, so a leaked API token was usable forever.
ExpiringTokenAuthentication now enforces settings.API_TOKEN_TTL_SECONDS, and
`get_user_api_token` rotates the key before expiry.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from Tracker.tests.base import TenantTestCase


class TokenExpiryTests(TenantTestCase):
    def _token_client(self, key, tenant):
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {key}",
            HTTP_X_TENANT_ID=str(tenant.id),
        )
        return client

    def test_expired_token_is_rejected(self):
        token = Token.objects.create(user=self.user_a)
        # `created` is auto_now_add, so backdate via update().
        Token.objects.filter(pk=token.pk).update(
            created=timezone.now() - timedelta(seconds=settings.API_TOKEN_TTL_SECONDS + 60)
        )
        resp = self._token_client(token.key, self.tenant_a).get("/api/Orders/")
        self.assertEqual(resp.status_code, 401, resp.content)

    def test_fresh_token_not_rejected_by_expiry(self):
        token = Token.objects.create(user=self.user_a)
        resp = self._token_client(token.key, self.tenant_a).get("/api/Orders/")
        # Auth succeeds (may be 200/403 on perms, but never 401 from expiry).
        self.assertNotEqual(resp.status_code, 401, resp.content)

    def test_token_endpoint_rotates_near_expiry(self):
        self.client.force_login(self.user_a)
        r1 = self.client.post("/api/user/token/")
        self.assertEqual(r1.status_code, 200, r1.content)
        key1 = r1.json()["token"]

        # Age the issued token past the 80% renewal threshold.
        Token.objects.filter(user=self.user_a).update(
            created=timezone.now() - timedelta(seconds=settings.API_TOKEN_TTL_SECONDS)
        )
        r2 = self.client.post("/api/user/token/")
        self.assertEqual(r2.status_code, 200, r2.content)
        key2 = r2.json()["token"]
        self.assertNotEqual(key1, key2, "token should rotate once it nears expiry")

    def test_token_endpoint_stable_within_window(self):
        """A fresh token is returned as-is on a subsequent fetch (no needless
        rotation that would invalidate an in-flight token)."""
        self.client.force_login(self.user_a)
        key1 = self.client.post("/api/user/token/").json()["token"]
        key2 = self.client.post("/api/user/token/").json()["token"]
        self.assertEqual(key1, key2)
