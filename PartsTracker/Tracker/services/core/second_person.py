"""Second-person (co-signature) authorization.

Authenticates a *different* user inline — without logging them in or touching
the acting user's session — so a second person standing at a shared terminal
can satisfy a gate that the person logged in cannot. This is the standard
DWI / regulated-manufacturing pattern: the operator's screen holds at a
buy-off point, the authorized person types their own credentials on that same
terminal, and their identity is what gets recorded.

Extracted from `StepExecutionViewSet._verify_supervisor`, which had been the
only implementation of this in the codebase and was hardcoded to the training
gate. It now serves any gate that needs a second person: the training-gate
override, execution reassignment, and (next) the FPI buy-off.

Note what this is *not*: `services/core/approval.py` and `services/qms/capa.py`
also verify a password, but the **acting** user's, as an e-signature on their
own action. That is a different thing — it proves who you are, not that
somebody else authorized you.

Contract — returns ``(authorizer, error)``:
  * ``(User, None)``  — a different, active user holding ``permission`` in
    this tenant.
  * ``(None, (detail, code, http_status))`` — credentials were supplied but
    rejected.
  * ``(None, None)`` — no credentials supplied at all. Callers treat this as
    "the caller didn't try to co-sign", which is distinct from a failure.

Behaviour pinned by ``Tracker/tests/test_second_person_throttle.py``. Two
details there are deliberate and easy to break in a rewrite:
  * once the throttle trips, even a *correct* password is refused — it is a
    throttle, not a hint;
  * a correct password that fails a later check (same-person, missing
    permission) consumes **no** throttle budget. Charging those would let a
    wrong-person mistake lock out the right person.
"""
from __future__ import annotations

from django.core.cache import cache
from rest_framework import status


# Default user-facing copy. Overridable per gate via `messages=` because the
# training gate's existing wording is already on screen in production and this
# extraction must not silently reword it.
DEFAULT_MESSAGES = {
    'throttled': 'Too many failed authorization attempts. Try again in a few minutes.',
    'auth_failed': 'Authorization failed - check the email and password.',
    'self': 'The authorizing person must be different from the person acting.',
    'not_permitted': 'That user is not authorized to do this.',
}


def verify_second_person(
    *,
    tenant,
    actor,
    email: str,
    password: str,
    permission: str,
    throttle_prefix: str,
    code_prefix: str,
    fail_cap: int = 5,
    fail_ttl: int = 900,
    messages: dict | None = None,
):
    """Authenticate a second person and check they hold ``permission``.

    Args:
        tenant: the tenant to scope the user lookup and the throttle to.
        actor: the currently-authenticated user; the authorizer must differ.
        email / password: the second person's credentials.
        permission: tenant permission codename the authorizer must hold.
        throttle_prefix: cache-key namespace for this gate's failure counter.
            **Must be distinct per gate.** The counter is keyed on the
            *authorizer's* email tenant-wide, so a shared prefix would let a
            typo at one gate lock that person out of every other gate.
        code_prefix: prefix for the returned error codes, so each gate can
            keep the codes its frontend already handles (``override_*`` for
            the training gate, ``cosign_*`` for FPI).
        fail_cap / fail_ttl: failures allowed, and the window in seconds.
        messages: optional overrides for the four user-facing strings, keyed
            ``throttled`` / ``auth_failed`` / ``self`` / ``not_permitted``.
            The training gate passes its original wording so extracting this
            helper doesn't reword text already in production.

    Returns:
        ``(authorizer, error)`` — see module docstring.
    """
    from Tracker.models import User

    msg = {**DEFAULT_MESSAGES, **(messages or {})}

    email = (email or '').strip()
    password = password or ''
    if not email and not password:
        return (None, None)

    tenant_id = getattr(tenant, 'id', 'none')
    throttle_key = f"{throttle_prefix}:{tenant_id}:{email.lower()}"

    # Rate-limit the password check so a shared terminal isn't a brute-force
    # oracle. Only failed *authentication* counts toward the cap. Checked
    # before authenticating, so a locked account is refused outright.
    if (cache.get(throttle_key) or 0) >= fail_cap:
        return (None, (msg['throttled'],
                       f'{code_prefix}_throttled',
                       status.HTTP_429_TOO_MANY_REQUESTS))

    # User's own manager isn't tenant-scoped — filter by tenant explicitly.
    authorizer = User.objects.filter(email__iexact=email, tenant=tenant).first()
    if not (authorizer and authorizer.is_active and authorizer.check_password(password)):
        cache.set(throttle_key, (cache.get(throttle_key) or 0) + 1, fail_ttl)
        return (None, (msg['auth_failed'],
                       f'{code_prefix}_auth_failed',
                       status.HTTP_403_FORBIDDEN))

    # Ordering matters: is_active/password precede these, so a wrong password
    # never reveals whether the account exists or what it can do.
    if authorizer.id == actor.id:
        return (None, (msg['self'],
                       f'{code_prefix}_self',
                       status.HTTP_403_FORBIDDEN))

    if not authorizer.has_tenant_perm(permission, tenant=tenant):
        return (None, (msg['not_permitted'],
                       f'{code_prefix}_not_permitted',
                       status.HTTP_403_FORBIDDEN))

    cache.delete(throttle_key)
    return (authorizer, None)
