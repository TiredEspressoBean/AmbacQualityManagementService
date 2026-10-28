"""The system-use notice shown at sign-in (NIST SP 800-171 3.1.9; user decision 2026-10-28).

Per tenant, in `Tenant.settings`, written by the shop on Settings → Organization; no default
text ships. Empty means nothing shows and nothing changes. When the tenant requires it, a
password sign-in must carry the acknowledgement, and the acknowledgement is recorded
(who, when, and which wording) as an access entry.

The sign-in page knows its tenant the way every request does (header / subdomain, or the
default tenant on a dedicated deployment). Where no tenant resolves — a SaaS address with
no subdomain — no notice can apply.
"""
from __future__ import annotations

import hashlib

NOTICE_KEY = 'sign_in_notice'
REQUIRE_ACK_KEY = 'sign_in_notice_requires_ack'


def sign_in_tenant(request):
    """The tenant a sign-in request is for. `/auth/` is exempt from TenantMiddleware, so
    resolve here the same way (header → subdomain, or the dedicated default); None when
    nothing resolves."""
    from Tracker.middleware import TenantMiddleware, TenantResolutionError
    try:
        tenant, _ = TenantMiddleware(lambda r: None)._resolve_tenant(request)
    except TenantResolutionError:
        return None
    return tenant


def notice_for(tenant) -> tuple[str, bool]:
    """(text, requires_ack) for `tenant`; ('', False) when there's no notice."""
    if tenant is None:
        return '', False
    settings = tenant.settings or {}
    text = (settings.get(NOTICE_KEY) or '').strip()
    if not text:
        return '', False
    return text, bool(settings.get(REQUIRE_ACK_KEY))


def record_acknowledgement(tenant, user, request) -> None:
    """Record that `user` acknowledged `tenant`'s notice at sign-in: an access entry with
    the time, address and a fingerprint of the wording they saw."""
    from Tracker.services.core.access_log import record_access
    from Tracker.throttling import get_client_ip
    text, _ = notice_for(tenant)
    record_access(
        obj=user, user=user, action_type='notice_acknowledged',
        object_repr=f'Acknowledged the system-use notice: {user}',
        remote_addr=get_client_ip(request),
        payload={'tenant': tenant.slug if tenant else None,
                 'notice_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()},
    )
