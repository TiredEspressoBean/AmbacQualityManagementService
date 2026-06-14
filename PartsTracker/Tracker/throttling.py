"""
Client-IP resolution + IP-based throttling that isn't spoofable behind a proxy.

The throttle key must be the *real* client IP. Behind a reverse proxy the TCP
`REMOTE_ADDR` is the proxy, and a raw `X-Forwarded-For` is client-supplied (the
leftmost entry is whatever the client claims). We therefore key on a TRUSTED,
edge-set header:

  - Railway sets `X-Real-IP` from the real connection (documented; not client-
    controllable). This is the default (`TRUSTED_CLIENT_IP_HEADER`).
  - On-prem behind a different proxy, set TRUSTED_CLIENT_IP_HEADER to
    'HTTP_X_FORWARDED_FOR' and NUM_PROXIES to the number of trusted proxies; the
    proxy-appended entry (counted from the right) is used, not the spoofable
    leftmost one.

Falls back to `REMOTE_ADDR` when no trusted header is present — a direct client,
or (safely) a shared proxy bucket, never a client-spoofable value.
"""

from django.conf import settings
from rest_framework.throttling import ScopedRateThrottle


def get_client_ip(request):
    """Return the trusted real client IP for `request` (see module docstring)."""
    header = getattr(settings, 'TRUSTED_CLIENT_IP_HEADER', '') or ''
    raw = request.META.get(header) if header else None
    if raw:
        parts = [p.strip() for p in raw.split(',') if p.strip()]
        if parts:
            if header == 'HTTP_X_FORWARDED_FOR':
                # client, proxy1, ..., trusted-edge — take NUM_PROXIES from the
                # right so client-prepended entries are ignored.
                n = getattr(settings, 'NUM_PROXIES', 1) or 1
                return parts[-min(n, len(parts))]
            # Single-value trusted header (e.g. X-Real-IP).
            return parts[0]
    return request.META.get('REMOTE_ADDR')


class ClientIPScopedRateThrottle(ScopedRateThrottle):
    """ScopedRateThrottle keyed on the trusted client IP rather than DRF's raw
    X-Forwarded-For handling, so the limit can't be bypassed by spoofing
    X-Forwarded-For."""

    def get_ident(self, request):
        return get_client_ip(request) or super().get_ident(request)
