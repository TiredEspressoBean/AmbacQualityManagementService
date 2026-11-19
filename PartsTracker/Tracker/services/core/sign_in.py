"""Getting someone signed in without email: invitations and admin-issued reset links.

The rule (user ruling 2026-11-19): no sign-in path depends on email. An invitation
and a reset link are both links an administrator hands over in person; email sends
them too where it's configured. They work the same way: one behaviour to learn.

- **Lifetime.** Whoever issues a link says how many days it works for: 1 to 30,
  7 unless they say otherwise (LINK_DAYS_DEFAULT — the bulk-user page and the
  workbook's later invites use it). A reset link sent by EMAIL (nobody chose its
  lifetime) works for EMAIL_RESET_DAYS.
- **Once.** An invitation is used up when accepted; a reset link when the password
  is set (its token hashes the old password).
- **One live invitation per person.** Accepting one, or resending, cancels the rest
  (cancelled = expired now). While one is pending, sending (Copy access link) returns
  the same link; Resend makes a new one for the days chosen.
- **An invitation only sets up an account that isn't set up** (no usable password):
  never a new password on a working one. A set-up account gets a reset link.
- **A reset link** is the same link the "forgot password" email carries (allauth's uid
  and token, so the existing Reset password page takes it). Issued only by someone who
  may invite (add_user), never for oneself, for a Tenant Admin only by a Tenant Admin,
  and only for an account that's set up. Kept as a PasswordResetLink: who, for whom,
  when, until when, used when (the token as a hash).
- **Any password reset signs the person out everywhere else**: their browser sessions
  and their API tokens.
"""
from __future__ import annotations

import hashlib
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

LINK_DAYS_DEFAULT = 7
LINK_DAYS_MAX = 30          # settings.PASSWORD_RESET_TIMEOUT is this, so no token outlives it
EMAIL_RESET_DAYS = 1

ALREADY_SET_UP = "This account is already set up — sign in, or ask your administrator for a reset link."
INVITE_EXPIRED = "This invitation has expired"
INVITE_REPLACED = "This invitation link was replaced by a newer one. Ask for the latest link."
INVITE_INVALID = "This invitation link isn't valid — check you have the whole link, or ask for a new one."
NOT_SET_UP = "Not set up yet — send an invitation instead."
LINK_EXPIRED = "This reset link has expired. Ask for a new one."
LINK_USED = "This reset link has already been used. Ask for a new one."
# An emailed link that was used (its token hashed the old password), or a mangled one.
LINK_INVALID = "This reset link is no longer valid — it may already have been used. Ask for a new one."


def link_days(value) -> int:
    """How long a link works, from what the issuer typed (blank: the default)."""
    if value in (None, ""):
        return LINK_DAYS_DEFAULT
    try:
        days = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Valid for is a number of days, 1 to {LINK_DAYS_MAX}.")
    if not 1 <= days <= LINK_DAYS_MAX:
        raise ValueError(f"Valid for is 1 to {LINK_DAYS_MAX} days.")
    return days


def is_set_up(user) -> bool:
    """Whether the account is set up: it has a usable password. The one rule for which
    link a person gets — set up: a reset link; not: an invitation — used by both actions
    and the User Management menu (via the row's is_set_up). Whether they've signed in
    yet doesn't enter into it. A user created without a password has an unusable (or,
    through the API, empty) one."""
    return bool(user.password) and user.has_usable_password()


def cancel_pending_invitations(user, *, keep=None) -> int:
    """Every pending invitation of `user` but `keep`, cancelled (expired now)."""
    from Tracker.models import UserInvitation
    now = timezone.now()
    pending = UserInvitation.objects.filter(user=user, accepted_at__isnull=True, expires_at__gt=now)
    if keep is not None:
        pending = pending.exclude(pk=keep.pk)
    return pending.update(expires_at=now)


def create_invitation(user, *, invited_by, days: int = LINK_DAYS_DEFAULT):
    """A new invitation for `user`, working for `days`, replacing any pending one."""
    from Tracker.models import UserInvitation
    cancel_pending_invitations(user)
    return UserInvitation.objects.create(
        user=user, invited_by=invited_by, token=UserInvitation.generate_token(),
        expires_at=timezone.now() + timedelta(days=days))


def invitation_refusal(invitation) -> str | None:
    """Why an invitation link can't set the account up, or None. A cancelled link is told
    apart from an expired one by what's recorded: a newer invitation for the same person
    (resend and send both replace through create_invitation)."""
    from Tracker.models import UserInvitation
    # Accepted: the account is set up — what the invitee needs is where to go next.
    if invitation.accepted_at or is_set_up(invitation.user):
        return ALREADY_SET_UP
    if invitation.is_valid():
        return None
    newer = UserInvitation.objects.filter(  # tenant-safe: by the user FK
        user_id=invitation.user_id, sent_at__gt=invitation.sent_at).exists()
    return INVITE_REPLACED if newer else INVITE_EXPIRED


def invitation_url(invitation) -> str:
    return f"{settings.FRONTEND_URL}/signup?token={invitation.token}"


def _is_tenant_admin(user, tenant) -> bool:
    if user.is_staff or user.is_superuser:
        return True
    return tenant is not None and "Tenant Admin" in user.get_tenant_group_names(tenant)


def reset_link_refusal(target, *, issuer, tenant) -> str | None:
    """Why `issuer` may not have a reset link for `target`, or None. The caller has
    already checked `issuer` may invite (add_user)."""
    if target.pk == issuer.pk:
        return "You can't issue a reset link for yourself — use Change password on your profile."
    if not is_set_up(target):
        return NOT_SET_UP
    if not target.is_active:
        return "This account is suspended — reactivate it first."
    if _is_tenant_admin(target, tenant) and not _is_tenant_admin(issuer, tenant):
        return "Only a Tenant Admin can issue a reset link for a Tenant Admin."
    return None


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def reset_link(target, *, issuer, days: int = LINK_DAYS_DEFAULT, remote_addr=None) -> dict:
    """The reset link for `target`: the email path's own link, valid once, for `days`.
    Kept as a PasswordResetLink (and in the audit log): who, for whom, when, until when."""
    from allauth.account.forms import default_token_generator
    from allauth.account.utils import user_pk_to_url_str
    from Tracker.models import PasswordResetLink
    from Tracker.services.core.access_log import record_access
    token = default_token_generator.make_token(target)
    expires_at = timezone.now() + timedelta(days=days)
    # The same account in the same second gives the same token: that's one link, re-issued.
    PasswordResetLink.objects.update_or_create(
        token_hash=_hash(token), defaults={'user': target, 'issued_by': issuer, 'expires_at': expires_at})
    record_access(obj=target, user=issuer, action_type='password_reset_link_issued',
                  payload={'for_user': target.pk, 'expires_at': expires_at.isoformat()},
                  remote_addr=remote_addr)
    return {'reset_url': f"{settings.FRONTEND_URL}/reset-password/{user_pk_to_url_str(target)}/{token}/",
            'expires_at': expires_at}


def _token_age(token: str) -> timedelta | None:
    """How long ago a reset token was made (Django's tokens carry their own timestamp)."""
    from allauth.account.forms import default_token_generator as gen
    from django.utils.http import base36_to_int
    try:
        made = base36_to_int((token or "").split("-")[0])
    except ValueError:
        return None
    return timedelta(seconds=gen._num_seconds(gen._now()) - made)


def reset_refusal(token: str) -> str | None:
    """Why a reset link can't be used now, beyond the token's own check: an issued link
    past its chosen lifetime, or already used; an emailed one past EMAIL_RESET_DAYS."""
    from Tracker.models import PasswordResetLink
    link = PasswordResetLink.objects.filter(token_hash=_hash(token or "")).first()
    if link is not None:
        if link.used_at is not None:
            return LINK_USED
        return LINK_EXPIRED if timezone.now() > link.expires_at else None
    age = _token_age(token)
    if age is not None and age > timedelta(days=EMAIL_RESET_DAYS):
        return LINK_EXPIRED
    return None


def reset_link_state(uid: str, token: str) -> str | None:
    """Why a reset link can't be used, checked when the page opens (so a spent or expired
    link says so before anyone types a password), or None when it works."""
    from allauth.account.forms import default_token_generator
    from allauth.account.utils import url_str_to_user_pk
    from django.contrib.auth import get_user_model
    refusal = reset_refusal(token)
    if refusal:
        return refusal
    try:
        user = get_user_model().objects.get(pk=url_str_to_user_pk(uid or ""))
    except Exception:  # noqa: BLE001 - a malformed or unknown uid is just a bad link
        return LINK_INVALID
    return None if default_token_generator.check_token(user, token or "") else LINK_INVALID


def sign_out_everywhere(user) -> int:
    """End every browser session and API token of `user`. Returns sessions ended.
    (Django already refuses a session whose password hash went stale; this also ends
    the API tokens, which a password change doesn't touch.)"""
    from django.contrib.sessions.models import Session
    from rest_framework.authtoken.models import Token
    Token.objects.filter(user=user).delete()
    ended = 0
    uid = str(user.pk)
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        if session.get_decoded().get("_auth_user_id") == uid:
            session.delete()
            ended += 1
    return ended


def after_password_reset(user, *, token: str = "", remote_addr=None) -> None:
    """A password was reset (an emailed or an issued link): an issued link is marked
    used, and the person is signed out everywhere else."""
    from Tracker.models import PasswordResetLink
    from Tracker.services.core.access_log import record_access
    PasswordResetLink.objects.filter(token_hash=_hash(token), used_at__isnull=True).update(
        used_at=timezone.now())
    sign_out_everywhere(user)
    record_access(obj=user, user=user, action_type='password_reset',
                  payload={'for_user': user.pk}, remote_addr=remote_addr)
