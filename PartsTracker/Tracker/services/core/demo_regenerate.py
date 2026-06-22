"""
Demo tenant regeneration — wipe + reseed back to a known state.

ONE specific tenant is supported: the one with `slug='demo'`. All entry
points refuse to operate on anything else. Two reasons:

  1. This is a hard-destructive operation. Wiping a real customer's
     tenant by accident is catastrophic.
  2. The reseed runs `seed_demo`, which encodes the *demo's* preset
     personas, orders, and parts. Running it on a real tenant would
     pollute that tenant with demo data.

Used by `TenantViewSet.regenerate_demo_data` (sync trigger) and the
matching Celery task (async path for the actual reseed).
"""
from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING

from django.core.management import call_command

if TYPE_CHECKING:
    from Tracker.models import Tenant


# The one tenant slug that may ever be regenerated. Hard-coded — *not*
# read from settings — because settings can be mis-configured per env
# but this guard must survive any config drift.
DEMO_TENANT_SLUG = "demo"


class DemoRegenerationRefused(Exception):
    """Raised when the regenerate target isn't the demo tenant."""


def regenerate_demo_data(tenant: "Tenant", *, acting_user) -> Dict[str, Any]:
    """Wipe + reseed the demo tenant.

    Args:
        tenant: must have `slug == 'demo'`. Anything else raises.
        acting_user: user who triggered the regen — recorded in the
            return summary for the audit log entry the viewset writes.

    Returns:
        dict with `{ok: True, slug, triggered_by_user_id, ...}`. Never
        returns on a non-demo tenant.

    The seed_demo management command itself owns the wipe order (it
    handles FK dependencies internally). We just kick it off here so
    the same trigger works both from `manage.py seed_demo` and from
    the API surface.
    """
    if tenant is None or getattr(tenant, "slug", None) != DEMO_TENANT_SLUG:
        raise DemoRegenerationRefused(
            f"regenerate_demo_data refuses non-demo tenant "
            f"(got slug={getattr(tenant, 'slug', None)!r}). "
            f"Only slug='{DEMO_TENANT_SLUG}' is supported."
        )

    # `seed_demo` defaults to clear+reseed (no --no-clear). It already
    # uses tenant_context internally, so the wipe is naturally scoped.
    call_command("seed_demo", verbosity=0)

    # Invalidate web sessions of demo-tenant users so already-open browsers
    # don't keep a stale session against freshly reseeded data, which can
    # wedge requests with a tenant/permission mismatch. Scoped to demo users —
    # other tenants' sessions are untouched. Bounced users just log in again
    # against the clean state.
    sessions_invalidated = _flush_tenant_user_sessions(tenant)

    # Media wipe: out-of-scope for this first cut. Demo media tends to
    # be a small set of seed assets that don't accumulate quickly; if
    # screenshots build up over time we'll wire S3-prefix deletion as
    # a follow-up. Flagging clearly in the return so the caller can
    # surface "media not wiped" if they want.
    return {
        "ok": True,
        "slug": tenant.slug,
        "triggered_by_user_id": getattr(acting_user, "id", None),
        "media_wiped": False,
        "sessions_invalidated": sessions_invalidated,
        "notes": "DB-only reseed; uploaded media (photos, 3D models, generated PDFs) retained.",
    }


def _flush_tenant_user_sessions(tenant: "Tenant") -> int:
    """Delete active web sessions belonging to users of ``tenant`` (its home
    users plus anyone holding a role in it).

    Django doesn't index sessions by user, so we scan unexpired sessions and
    match the decoded ``_auth_user_id`` — fine at demo scale. Scoped to this
    tenant's users so a demo reseed never logs out other tenants. Returns the
    count deleted.
    """
    from django.contrib.auth import get_user_model
    from django.contrib.sessions.models import Session
    from django.utils import timezone

    from Tracker.models import UserRole

    User = get_user_model()
    user_ids = set(
        User.objects.filter(tenant=tenant).values_list("id", flat=True)
    ) | set(
        UserRole.objects.filter(group__tenant=tenant).values_list("user_id", flat=True)
    )
    if not user_ids:
        return 0
    user_ids = {str(uid) for uid in user_ids}

    deleted = 0
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        if session.get_decoded().get("_auth_user_id") in user_ids:
            session.delete()
            deleted += 1
    return deleted
