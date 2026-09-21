"""One way to record that someone *read* something.

Model changes are handled by django-auditlog's signals, inside the request
transaction, so a failure there rolls the write back. Access logging is
different: nothing is being changed, the read has usually already happened by
the time we record it, and the record is written by hand at a handful of call
sites.

Those call sites had drifted into three different failure behaviours — one
propagated, one warned, one used `print()`. This module exists so there is a
single answer.

**The policy: non-fatal, but loud.**

A failure to write the access record does not fail the request. Blocking a
shop-floor operator from opening a drawing because the audit table hiccuped
trades a real outage for a bookkeeping problem, and the read has already
occurred regardless — refusing afterwards records nothing extra.

But it is logged at ERROR with a traceback, to a dedicated logger
(`compliance.access_control`), with `audit_write_failed` in the payload so it
can be alerted on. That last part is the point. NIST 800-171 3.3.4 asks to be
told when audit logging fails; it does not ask for the request to die. A
silent warning in application output is what fails that practice, not the
decision to continue.

If you add another access-logging call site, use `record_access()` rather
than writing `LogEntry.objects.create` again.
"""
from __future__ import annotations

import logging

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

logger = logging.getLogger('compliance.access_control')

# What the audit row's `changes` carries, and what the compliance logger emits,
# are deliberately the same dict: one payload, two destinations, so a SIEM and
# the in-app log agree about what happened.


def record_access(
    *,
    obj,
    user,
    action_type: str,
    payload: dict | None = None,
    remote_addr: str | None = None,
    object_repr: str | None = None,
):
    """Record that `user` read `obj`. Never raises.

    Args:
        obj: The instance that was accessed, or a model *class* when the
            access has no single subject — an AI query across a table, say.
            A class records an empty `object_pk`, which is what the query
            case wants.
        user: The accessor. May be anonymous; stored as null actor.
        action_type: Short verb for the event, e.g. 'document_view',
            'document_download', 'ai_query'.
        payload: Extra structured detail, merged into both destinations.
        remote_addr: Trusted client IP, if the caller has a request.
        object_repr: Override for the human-readable label, for cases where
            `str(obj)` is not the useful thing (an AI query over a model
            class, say).

    Returns:
        True if the audit row was written, False if it failed. Callers do not
        have to check — the point of the return value is testability.
    """
    from auditlog.models import LogEntry

    data = {'action_type': action_type, **(payload or {})}
    actor = user if getattr(user, 'is_authenticated', False) else None
    # A class has a `pk` descriptor rather than a value, so guard on that
    # instead of relying on getattr returning something str()-able.
    object_pk = '' if isinstance(obj, type) else str(getattr(obj, 'pk', '') or '')

    try:
        LogEntry.objects.create(
            content_type=ContentType.objects.get_for_model(obj),
            object_pk=object_pk,
            object_repr=object_repr or str(obj),
            action=LogEntry.Action.ACCESS,
            changes=data,
            actor=actor,
            timestamp=timezone.now(),
            remote_addr=remote_addr,
        )
    except Exception:
        # Loud on purpose -- see the module docstring. ERROR with a traceback,
        # and a stable marker so this is alertable without parsing prose.
        logger.error(
            'audit_write_failed: could not record %s access for user %s',
            action_type,
            getattr(user, 'pk', None),
            exc_info=True,
            extra={'audit_write_failed': True, 'action_type': action_type},
        )
        return False

    # The compliance trail is a separate destination from the audit row, so a
    # SIEM can consume it without reading the database. Emitted only on a
    # successful write: a failed write already produced an ERROR above, and
    # emitting both would make the failure look like a successful access.
    logger.info(
        'access_granted: %s',
        action_type,
        extra={
            'event_type': 'ACCESS_GRANTED',
            'action_type': action_type,
            'user_id': str(getattr(user, 'pk', '') or ''),
            'remote_addr': remote_addr,
            **data,
        },
    )
    return True
