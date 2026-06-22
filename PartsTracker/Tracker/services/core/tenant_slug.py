"""Tenant slug validation shared by the signup/admin serializers and the
subdomain resolver in ``TenantMiddleware``.

In SaaS mode a tenant slug becomes a live subdomain under
``TENANT_BASE_DOMAIN`` (e.g. ``acme`` -> ``acme.uqmes.com``), so a slug must be
a valid DNS label AND must not collide with reserved infrastructure
subdomains. Both rules live here so the middleware and the serializers can't
drift apart (previously the middleware hardcoded ``['www', 'api']`` while the
serializers enforced neither).
"""
from __future__ import annotations

import re

from django.conf import settings

# RFC-1035 DNS label: lowercase alphanumerics + hyphens, 1-63 chars, no
# leading/trailing hyphen. Underscores are intentionally rejected — they're
# invalid in hostnames even though Django's SlugField permits them.
_DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def reserved_slugs() -> set[str]:
    """The set of slugs that may not be used as a tenant slug. Sourced from
    ``settings.RESERVED_TENANT_SLUGS`` so it's tunable per deployment."""
    return {s.lower() for s in getattr(settings, "RESERVED_TENANT_SLUGS", [])}


def is_reserved_slug(slug: str | None) -> bool:
    return (slug or "").lower() in reserved_slugs()


def validate_tenant_slug(value: str | None) -> str:
    """Return the normalized (lower-cased) slug, or raise ``ValueError`` with a
    user-facing message. For slugs that will become subdomains."""
    slug = (value or "").strip().lower()
    if not _DNS_LABEL.match(slug):
        raise ValueError(
            "Organization URL must be a valid subdomain: lowercase letters, "
            "digits, and hyphens only (no underscores), 1-63 characters, and "
            "may not start or end with a hyphen."
        )
    if slug in reserved_slugs():
        raise ValueError(
            f"'{slug}' is reserved and cannot be used as an organization URL."
        )
    return slug
