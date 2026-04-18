"""
Integration webhook receiver.

URL-routed: each integration gets a unique webhook URL containing the integration UUID.
Signature verification first, then idempotency check, then dispatch to provider handler.
"""

import hashlib
import json
import logging

from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from hubspot.utils.signature import Signature
from hubspot.exceptions import InvalidSignatureTimestampError

from integrations.models.config import IntegrationConfig, ProcessedWebhook
from integrations.services.registry import get_adapter

logger = logging.getLogger(__name__)


def _verify_hubspot_signature(request, integration):
    """Verify HubSpot webhook signature using the official SDK.

    Tries v3 first (HMAC-SHA256 with timestamp validation), falls back to v2
    (SHA256 of secret + method + uri + body).
    """
    secret = integration.webhook_secret
    if not secret:
        logger.warning(
            "Webhook received for integration %s with no webhook_secret configured",
            integration.id,
        )
        return False

    # Try v3 first (most secure — includes timestamp expiry)
    sig_v3 = request.headers.get('X-HubSpot-Signature-v3', '')
    timestamp = request.headers.get('X-HubSpot-Request-Timestamp', '')

    if sig_v3 and timestamp:
        try:
            return Signature.is_valid(
                signature=sig_v3,
                client_secret=secret,
                request_body=request.body.decode(),
                http_uri=request.build_absolute_uri(),
                http_method=request.method,
                signature_version='v3',
                timestamp=timestamp,
            )
        except InvalidSignatureTimestampError:
            logger.warning(
                "HubSpot webhook timestamp expired for integration %s",
                integration.id,
            )
            return False

    # Fall back to v2
    sig_v2 = request.headers.get('X-HubSpot-Signature', '')
    if sig_v2:
        return Signature.is_valid(
            signature=sig_v2,
            client_secret=secret,
            request_body=request.body.decode(),
            http_uri=request.build_absolute_uri(),
            http_method=request.method,
            signature_version='v2',
        )

    return False


def _extract_event_id(request, provider):
    """Extract a unique event identifier for idempotency."""
    if provider == 'hubspot':
        try:
            payload = json.loads(request.body)
            events = payload if isinstance(payload, list) else [payload]
            # Use first event's ID + timestamp as idempotency key
            if events:
                event = events[0]
                return f"{event.get('eventId', '')}-{event.get('occurredAt', '')}"
        except (json.JSONDecodeError, KeyError):
            pass
    # Fallback: hash the body
    return hashlib.sha256(request.body).hexdigest()


SIGNATURE_VERIFIERS = {
    'hubspot': _verify_hubspot_signature,
}


@csrf_exempt
def integration_webhook(request, provider, integration_id):
    """
    Receive and process an integration webhook.

    URL: /webhooks/<provider>/<integration_id>/
    """
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')

    integration = get_object_or_404(
        IntegrationConfig, id=integration_id, provider=provider, is_enabled=True
    )

    # Signature verification FIRST
    verifier = SIGNATURE_VERIFIERS.get(provider)
    if verifier and not verifier(request, integration):
        return HttpResponseForbidden('Invalid signature')

    # Idempotency check
    event_id = _extract_event_id(request, provider)
    if ProcessedWebhook.objects.filter(
        integration=integration, external_event_id=event_id
    ).exists():
        return JsonResponse({'status': 'already_processed'})

    # Dispatch to provider-specific handler
    adapter = get_adapter(provider)
    result = adapter.handle_webhook(request, integration)

    # Record as processed
    ProcessedWebhook.objects.create(
        integration=integration,
        external_event_id=event_id,
        tenant=integration.tenant,
    )

    return JsonResponse(result)
