"""
Security-audit regression for rate limiting on unauthenticated auth endpoints.

Signup, registration, login, and password-reset were `AllowAny` with no throttle
anywhere — open to mass account/tenant creation, credential brute-force, reset-
email bombing, and email enumeration. ScopedRateThrottle now bounds each by IP.
"""

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class AuthThrottleTests(TestCase):
    def setUp(self):
        cache.clear()  # throttle counters live in the cache
        self.client = APIClient()

    def _hammer(self, url, payload, n):
        return [self.client.post(url, payload, format='json').status_code for _ in range(n)]

    def test_signup_is_throttled(self):
        # rate 5/hour → the 6th+ request is rejected with 429.
        statuses = self._hammer('/api/tenants/signup/', {}, 7)
        self.assertIn(429, statuses, f"signup not throttled; statuses={statuses}")
        self.assertNotEqual(statuses[0], 429, "first request must not be throttled")

    def test_password_reset_is_throttled(self):
        statuses = self._hammer('/auth/password/reset/', {'email': 'x@example.com'}, 7)
        self.assertIn(429, statuses, f"password reset not throttled; statuses={statuses}")

    def test_login_is_throttled(self):
        # rate 10/min → the 11th+ request is rejected.
        statuses = self._hammer('/auth/login/', {'username': 'x', 'password': 'y'}, 12)
        self.assertIn(429, statuses, f"login not throttled; statuses={statuses}")

    def test_registration_is_throttled(self):
        statuses = self._hammer('/auth/registration/', {}, 7)
        self.assertIn(429, statuses, f"registration not throttled; statuses={statuses}")

    def test_spoofed_xff_does_not_bypass_throttle(self):
        """Rotating X-Forwarded-For per request must NOT mint new buckets — the
        throttle keys on the trusted client IP, not the spoofable XFF header."""
        statuses = [
            self.client.post(
                '/api/tenants/signup/', {}, format='json',
                HTTP_X_FORWARDED_FOR=f'10.0.0.{i}',  # attacker-rotated, must be ignored
            ).status_code
            for i in range(7)
        ]
        self.assertIn(429, statuses, f"spoofed XFF bypassed throttle; statuses={statuses}")

    def test_trusted_real_ip_is_per_client(self):
        """X-Real-IP (the trusted, edge-set header) is the key: one IP hitting
        the limit doesn't throttle a different IP."""
        for _ in range(6):  # exhaust 1.1.1.1 (signup rate 5/hour)
            self.client.post('/api/tenants/signup/', {}, format='json', HTTP_X_REAL_IP='1.1.1.1')
        same = self.client.post('/api/tenants/signup/', {}, format='json', HTTP_X_REAL_IP='1.1.1.1')
        other = self.client.post('/api/tenants/signup/', {}, format='json', HTTP_X_REAL_IP='2.2.2.2')
        self.assertEqual(same.status_code, 429, "exhausted IP should be throttled")
        self.assertNotEqual(other.status_code, 429, "a different real IP must have its own bucket")
