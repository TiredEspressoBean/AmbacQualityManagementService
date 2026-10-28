"""django-auditlog's middleware, recording the trusted client address.

`AuditlogMiddleware` stores the FIRST X-Forwarded-For entry as `LogEntry.remote_addr` —
the one the client controls, so any change record's IP could be forged by sending the
header. Approvals, QA release and the access log already use the app's trusted
`get_client_ip` (Tracker/throttling.py: the configured header, read from the right past
NUM_PROXIES). Change records now use it too (user decision 2026-10-28). Everything else —
actor, port, correlation id, AUDITLOG_DISABLE_REMOTE_ADDR — is the library's own.
"""
from auditlog.middleware import AuditlogMiddleware

from Tracker.throttling import get_client_ip


class TrustedIPAuditlogMiddleware(AuditlogMiddleware):

    @staticmethod
    def _get_remote_addr(request):
        from django.conf import settings
        if settings.AUDITLOG_DISABLE_REMOTE_ADDR:
            return None
        remote_addr = get_client_ip(request)
        if not remote_addr:
            return None
        # Strip a port, as the library does.
        if "." in remote_addr and ":" in remote_addr:  # IPv4 with port (`x.x.x.x:x`)
            remote_addr = remote_addr.split(":")[0]
        elif "[" in remote_addr:  # IPv6 with port (`[:::]:x`)
            remote_addr = remote_addr[1:].split("]")[0]
        return remote_addr
