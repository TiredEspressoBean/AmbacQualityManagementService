"""
Coverage guard for Row-Level Security (RLS) policies.

`setup_rls.py` enables RLS + the tenant-isolation policy on a HAND-MAINTAINED
list of tables (`Command.TENANT_SCOPED_TABLES`). Any tenant-scoped model whose
table is not in that list gets NO database-level policy — so if RLS is the
intended defense-in-depth backstop, those tables are silently unprotected.

This test discovers every concrete model with a `tenant` FK and asserts its
table is covered by the list. It mirrors the manager-coverage lint in
test_tenant_scoping_lint.py, but for the RLS layer.

KNOWN_UNCOVERED is a frozen baseline of the tables that were already missing
when this guard was added (audit, 2026-06). It exists so the guard can be
landed without forcing a same-PR backfill of `setup_rls.py`. The guard is
two-directional, so the baseline can only shrink:

  * a NEW tenant-scoped model added without coverage (and not in the baseline)
    fails the test — this is the anti-drift guarantee;
  * a baseline table that becomes covered (or is removed) fails the test until
    it is also removed from the baseline — so fixing the debt forces the
    baseline to stay honest.

Burn-down: as `setup_rls.py` gains entries, delete the corresponding lines
here. When KNOWN_UNCOVERED is empty, delete it and the baseline branch.
"""

from django.apps import apps
from django.test import SimpleTestCase

from Tracker.management.commands.setup_rls import Command


# Tables that legitimately should NOT carry a tenant-isolation policy even
# though their model has a `tenant` FK. Keep empty unless there is a real
# reason (documented inline). NOT for "we haven't gotten to it yet" — that is
# KNOWN_UNCOVERED.
INTENTIONALLY_EXEMPT = frozenset({
    # TenantMembership IS the access-control table: the tenant-isolation access
    # check queries it to DECIDE access, which runs BEFORE the request's tenant
    # context / RLS GUC is established. An RLS tenant-isolation policy would
    # filter it to zero rows during that pre-context query and break the check.
    # It is never exposed to end users in a list form; the service always
    # queries it filtered by an explicit (user, tenant) pair. See
    # Tracker.models.TenantMembership and services.core.tenant_membership.
    'tracker_tenant_membership',
})

# Baseline of tables uncovered when the guard was introduced. The audit
# backfill (2026-06) added all of them to setup_rls.py, so this is now empty:
# the guard enforces FULL coverage. If you must temporarily defer a table,
# add it here with a comment rather than weakening the assertion.
KNOWN_UNCOVERED = frozenset()


class RLSPolicyCoverageTests(SimpleTestCase):
    @staticmethod
    def _tenant_scoped_tables():
        """db_table for every concrete model with a `tenant` FK to Tenant."""
        tables = set()
        for model in apps.get_models():
            for field in model._meta.get_fields():
                related = getattr(field, "related_model", None)
                if related is not None and related.__name__ == "Tenant" and field.name == "tenant":
                    tables.add(model._meta.db_table)
                    break
        return tables

    def test_every_tenant_scoped_table_has_rls_or_is_baselined(self):
        # setup_rls matches tables case-insensitively (ILIKE), so compare lower.
        listed = {t.lower() for t in Command.TENANT_SCOPED_TABLES}
        baseline = {t.lower() for t in KNOWN_UNCOVERED}
        exempt = {t.lower() for t in INTENTIONALLY_EXEMPT}

        all_tables = self._tenant_scoped_tables()
        uncovered = {t for t in all_tables if t.lower() not in listed and t.lower() not in exempt}

        # Direction 1: new drift — uncovered and not in the baseline.
        new_drift = {t for t in uncovered if t.lower() not in baseline}
        # Direction 2: stale baseline — listed in the baseline but now covered
        # or no longer a tenant-scoped table.
        all_lower = {t.lower() for t in all_tables}
        stale_baseline = {
            t for t in baseline
            if t in listed or t in exempt or t not in all_lower
        }

        msgs = []
        if new_drift:
            msgs.append(
                "Tenant-scoped tables with NO RLS policy (add them to "
                "setup_rls.py TENANT_SCOPED_TABLES, or — only with a documented "
                "reason — to INTENTIONALLY_EXEMPT):\n  "
                + "\n  ".join(sorted(new_drift))
            )
        if stale_baseline:
            msgs.append(
                "KNOWN_UNCOVERED baseline is stale — these are now covered (or "
                "no longer tenant-scoped). Remove them from KNOWN_UNCOVERED:\n  "
                + "\n  ".join(sorted(stale_baseline))
            )
        if msgs:
            self.fail("\n\n".join(msgs))
