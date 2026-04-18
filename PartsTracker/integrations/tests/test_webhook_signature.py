"""
Tests for webhook signature verification.

Covers:
- HubSpot v2 and v3 signature validation via the SDK
- Rejection when no webhook_secret is configured
- Rejection when no signature headers are present
- Expired v3 timestamps
"""

import hashlib
import hmac
import base64
import time
from unittest.mock import MagicMock, patch

from django.test import TestCase, RequestFactory, override_settings

from integrations.webhooks.views import _verify_hubspot_signature


def _make_request(body=b'[]', headers=None):
    """Build a fake Django request with the given body and headers."""
    factory = RequestFactory()
    request = factory.post(
        '/webhooks/hubspot/00000000-0000-0000-0000-000000000001/',
        data=body,
        content_type='application/json',
    )
    request._body = body
    # Apply extra headers
    if headers:
        for key, value in headers.items():
            # RequestFactory uses META keys (HTTP_ prefix, uppercase, hyphens -> underscores)
            meta_key = 'HTTP_' + key.upper().replace('-', '_')
            request.META[meta_key] = value
    return request


def _make_integration(webhook_secret='test-secret'):
    """Build a mock IntegrationConfig."""
    integration = MagicMock()
    integration.id = '00000000-0000-0000-0000-000000000001'
    integration.webhook_secret = webhook_secret
    return integration


@override_settings(ALLOWED_HOSTS=['testserver'])
class HubSpotSignatureV2Tests(TestCase):
    """Tests for v2 signature verification (SHA256 of secret+method+uri+body)."""

    def _compute_v2_signature(self, secret, method, uri, body):
        """Compute a valid v2 signature the way HubSpot does it."""
        source = secret + method + uri + body
        return hashlib.sha256(source.encode()).hexdigest()

    def test_valid_v2_signature_accepted(self):
        body = b'[{"eventId": 1}]'
        integration = _make_integration('my-secret')
        request = _make_request(body=body)
        uri = request.build_absolute_uri()

        sig = self._compute_v2_signature('my-secret', 'POST', uri, body.decode())
        request.META['HTTP_X_HUBSPOT_SIGNATURE'] = sig

        self.assertTrue(_verify_hubspot_signature(request, integration))

    def test_invalid_v2_signature_rejected(self):
        body = b'[{"eventId": 1}]'
        integration = _make_integration('my-secret')
        request = _make_request(body=body, headers={
            'X-HubSpot-Signature': 'deadbeef' * 8,
        })

        self.assertFalse(_verify_hubspot_signature(request, integration))

    def test_tampered_body_rejected(self):
        body = b'[{"eventId": 1}]'
        integration = _make_integration('my-secret')
        request = _make_request(body=body)
        uri = request.build_absolute_uri()

        # Sign a different body
        sig = self._compute_v2_signature('my-secret', 'POST', uri, 'tampered')
        request.META['HTTP_X_HUBSPOT_SIGNATURE'] = sig

        self.assertFalse(_verify_hubspot_signature(request, integration))


@override_settings(ALLOWED_HOSTS=['testserver'])
class HubSpotSignatureV3Tests(TestCase):
    """Tests for v3 signature verification (HMAC-SHA256 with timestamp)."""

    def _compute_v3_signature(self, secret, method, uri, body, timestamp):
        """Compute a valid v3 signature the way HubSpot does it."""
        source = method + uri + body + timestamp
        raw = hmac.new(
            secret.encode(), source.encode(), hashlib.sha256
        ).digest()
        return base64.b64encode(raw).decode()

    def test_valid_v3_signature_accepted(self):
        body = b'[{"eventId": 1}]'
        integration = _make_integration('my-secret')
        timestamp = str(int(time.time() * 1000))
        request = _make_request(body=body)
        uri = request.build_absolute_uri()

        sig = self._compute_v3_signature(
            'my-secret', 'POST', uri, body.decode(), timestamp
        )
        request.META['HTTP_X_HUBSPOT_SIGNATURE_V3'] = sig
        request.META['HTTP_X_HUBSPOT_REQUEST_TIMESTAMP'] = timestamp

        self.assertTrue(_verify_hubspot_signature(request, integration))

    def test_expired_v3_timestamp_rejected(self):
        body = b'[{"eventId": 1}]'
        integration = _make_integration('my-secret')
        # Timestamp 10 minutes ago (SDK allows 300s max)
        timestamp = str(int((time.time() - 600) * 1000))
        request = _make_request(body=body)
        uri = request.build_absolute_uri()

        sig = self._compute_v3_signature(
            'my-secret', 'POST', uri, body.decode(), timestamp
        )
        request.META['HTTP_X_HUBSPOT_SIGNATURE_V3'] = sig
        request.META['HTTP_X_HUBSPOT_REQUEST_TIMESTAMP'] = timestamp

        self.assertFalse(_verify_hubspot_signature(request, integration))

    def test_v3_preferred_over_v2_when_both_present(self):
        """When both v2 and v3 headers are present, v3 is used."""
        body = b'[{"eventId": 1}]'
        integration = _make_integration('my-secret')
        timestamp = str(int(time.time() * 1000))
        request = _make_request(body=body)
        uri = request.build_absolute_uri()

        v3_sig = self._compute_v3_signature(
            'my-secret', 'POST', uri, body.decode(), timestamp
        )
        request.META['HTTP_X_HUBSPOT_SIGNATURE_V3'] = v3_sig
        request.META['HTTP_X_HUBSPOT_REQUEST_TIMESTAMP'] = timestamp
        # Provide an invalid v2 sig — should still pass because v3 is preferred
        request.META['HTTP_X_HUBSPOT_SIGNATURE'] = 'invalid'

        self.assertTrue(_verify_hubspot_signature(request, integration))


@override_settings(ALLOWED_HOSTS=['testserver'])
class HubSpotSignatureEdgeCaseTests(TestCase):
    """Tests for edge cases in signature verification."""

    def test_no_secret_configured_rejects(self):
        """Webhook rejected when integration has no webhook_secret."""
        request = _make_request(headers={
            'X-HubSpot-Signature': 'anything',
        })
        integration = _make_integration(webhook_secret='')

        self.assertFalse(_verify_hubspot_signature(request, integration))

    def test_no_secret_rejects_even_in_debug_mode(self):
        """DEBUG=True no longer bypasses signature verification."""
        request = _make_request(headers={
            'X-HubSpot-Signature': 'anything',
        })
        integration = _make_integration(webhook_secret='')

        with self.settings(DEBUG=True):
            self.assertFalse(_verify_hubspot_signature(request, integration))

    def test_no_signature_headers_rejects(self):
        """No signature headers at all -> rejected."""
        request = _make_request()
        integration = _make_integration('my-secret')

        self.assertFalse(_verify_hubspot_signature(request, integration))
