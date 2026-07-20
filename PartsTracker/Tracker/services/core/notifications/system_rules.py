"""
System-seeded NotificationRule starter set.

When a Tenant is created, `seed_system_rules_for_tenant()` populates a
sensible default set of rules so the notification surface isn't empty
on day one. Admins customize from there.

Idempotent: re-running on a tenant that already has a starter rule with
the same name leaves it untouched. The name is the natural key for
re-seeding — tenants who delete a starter rule get it back on re-seed.
If you don't want that, customize the name or remove the rule via
post_save customization.

Each starter rule is keyed by event + a stable "system rule name" so
admins recognize them in the UI ("CAPA assignments — route to assignee"
is more meaningful than "rule #1").

The starter set is intentionally conservative — events we've actually
shipped templates for AND have a sensible default routing.
"""
from __future__ import annotations

import logging
from typing import Iterable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Starter rule specs
# ---------------------------------------------------------------------------
# Each spec is (event_code, name, recipient_strategy, recipient_group_names,
# channels, description). Lookups are by display name so they match the
# group names seeded by GroupSeeder for new tenants.

STARTER_RULES = [
    # ---- Quality / NCR ---------------------------------------------------
    {
        "event_code": "ncr.opened",
        "name": "NCRs — route to QA Manager",
        "description": "Default starter rule. QA Manager group gets every NCR opened in this tenant.",
        "recipient_strategy": "static",
        "recipient_group_names": ["QA Manager"],
        "channels": ["in_app", "email"],
        "min_gap_seconds": 0,
    },
    {
        "event_code": "quality.step_failure",
        "name": "Step failures — route to QA",
        "description": "Default starter rule. QA Manager and Inspector groups get every step failure.",
        "recipient_strategy": "static",
        "recipient_group_names": ["QA Manager", "QA Inspector"],
        "channels": ["in_app", "email"],
        "min_gap_seconds": 0,
    },

    # ---- CAPA ------------------------------------------------------------
    # Per-instance routing — recipient is the assignee, set by the signal.
    # No static recipients on this rule.
    {
        "event_code": "capa.assigned",
        "name": "CAPA assignments — route to assignee",
        "description": "Default starter rule. The CAPA's assignee gets notified on create or reassignment.",
        "recipient_strategy": "from_payload",
        "recipient_group_names": [],
        "channels": ["in_app", "email"],
        "min_gap_seconds": 0,
    },
    {
        "event_code": "capa.ready_for_verification",
        "name": "CAPA ready for verification — route to QA Manager",
        "description": "Default starter rule. QA Manager group is notified when a CAPA's tasks and RCA are complete and it's ready for effectiveness verification.",
        "recipient_strategy": "static",
        "recipient_group_names": ["QA Manager"],
        "channels": ["in_app", "email"],
        "min_gap_seconds": 0,
    },

    # ---- Work orders -----------------------------------------------------
    {
        "event_code": "workorder.overdue",
        "name": "Overdue work orders — route to Production",
        "description": "Default starter rule. Production Manager group gets every overdue work order.",
        "recipient_strategy": "static",
        "recipient_group_names": ["Production Manager"],
        "channels": ["in_app"],
        "min_gap_seconds": 0,
    },
    {
        "event_code": "workorder.held",
        "name": "Held work orders — route to Production",
        "description": "Default starter rule. Production Manager group gets work orders held too long.",
        "recipient_strategy": "static",
        "recipient_group_names": ["Production Manager"],
        "channels": ["in_app"],
        "min_gap_seconds": 0,
    },
    {
        "event_code": "shift_note.published",
        "name": "Shift notes — alert the audience",
        "description": "Default starter rule. The note's audience gets alerted, routed via payload.recipient_user_ids.",
        "recipient_strategy": "from_payload",
        "recipient_group_names": [],
        "channels": ["in_app"],
        "min_gap_seconds": 0,
    },
]


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------

def seed_system_rules_for_tenant(tenant) -> dict[str, int]:
    """Seed the starter rule set for a tenant. Idempotent.

    Skips events not registered in EVENT_REGISTRY (allows rule specs to be
    added before/after their event registrations). Skips group references
    that don't resolve on this tenant.

    Must be called from within the tenant's context (the caller sets
    `tenant_context(tenant.id)` before invoking).

    Returns a counts dict: `{'created': N, 'skipped': M, 'errors': K}`.
    """
    from Tracker.models import NotificationRule, TenantGroup
    from .registry import EVENT_REGISTRY

    created = 0
    skipped = 0
    errors = 0

    # Pre-fetch tenant groups by name for O(1) lookup.
    groups_by_name: dict[str, TenantGroup] = {
        g.name: g for g in TenantGroup.objects.filter(tenant=tenant)
    }

    for spec in STARTER_RULES:
        event_code = spec["event_code"]
        if event_code not in EVENT_REGISTRY:
            logger.debug(
                "system rules: skipping %r — event not registered for tenant %s",
                event_code, tenant.id,
            )
            skipped += 1
            continue

        name = spec["name"]
        # Idempotency: skip if a rule with this name already exists for the event.
        if NotificationRule.objects.filter(
            tenant=tenant, event_code=event_code, name=name,
        ).exists():
            skipped += 1
            continue

        # Resolve recipient groups by name; warn (not error) if a referenced
        # group doesn't exist on this tenant.
        resolved_groups = []
        for group_name in spec["recipient_group_names"]:
            group = groups_by_name.get(group_name)
            if group is None:
                logger.warning(
                    "system rules: starter rule %r references group %r "
                    "which doesn't exist on tenant %s — group skipped",
                    name, group_name, tenant.id,
                )
                continue
            resolved_groups.append(group)

        try:
            rule = NotificationRule.objects.create(
                tenant=tenant,
                name=name,
                description=spec["description"],
                event_code=event_code,
                scope_kind="tenant",
                conditions_source="",
                channels=spec["channels"],
                recipient_strategy=spec["recipient_strategy"],
                min_gap_seconds=spec["min_gap_seconds"],
                enabled=True,
            )
            if resolved_groups:
                rule.recipient_groups.add(*resolved_groups)
            created += 1
        except Exception:
            logger.exception(
                "system rules: failed to create starter rule %r for tenant %s",
                name, tenant.id,
            )
            errors += 1

    logger.info(
        "system rules: tenant=%s created=%d skipped=%d errors=%d",
        tenant.id, created, skipped, errors,
    )
    return {"created": created, "skipped": skipped, "errors": errors}


def list_starter_rule_specs() -> Iterable[dict]:
    """Read-only view of the starter rule specs. Useful for tests and admin
    "show me what would be seeded" tooling."""
    return tuple(STARTER_RULES)
