"""
Permission coverage guard.

Every Tracker permission must be *accounted for*: either granted to a preset
group in ``Tracker.presets.GROUP_PRESETS``, or explicitly opted out here with a
reason. An "orphaned" perm — granted to no group and not opted out — is only
held by the System Admin ``'__all__'`` role, so every other role hits a 403 the
moment a UI surfaces it. That's how ``view_samplingdecision``, ``view_substep``,
and the reman grading actions silently broke.

Intentional non-grants are expressed as **model-level rules** (a model + a
permission type), so a new model in an already-adjudicated category is covered
without enumerating its four perms. The actual gaps still to be granted live in
the explicit ``KNOWN_GAPS`` burn-down list.

When this test fails:
  * **Unexplained orphan** — granted to no group and matched by no opt-out rule.
    Grant it in ``presets.py``; or, if intentionally ungranted, extend the right
    ``*_MODELS`` set / ``KNOWN_GAPS`` *with a reason*.
  * **Stale KNOWN_GAPS** — a gap that's now granted (or gone). Remove it; that's
    the burn-down working.

``KNOWN_GAPS`` must trend to empty (each removal pairs with a grant). The
``*_MODELS`` rules are the permanent, adjudicated intent.
"""
from django.contrib.auth.models import Permission
from django.test import TestCase

from Tracker.presets import GROUP_PRESETS


# Every perm (add/change/delete/view) is System-Admin-only: tenant + platform
# configuration, integration internals, notification config/dispatcher
# internals, escalation config/instances. No operational role manages these.
ADMIN_ONLY_MODELS = {
    'tenant', 'tenantllmprovider',
    'tenantnotificationbranding', 'tenantnotificationdefault',
    'usernotificationpreference',          # per-user prefs (self-service via /me)
    'hubspotsynclog', 'externalcontact',   # integration / external contacts
    'artifactsequence',                    # change-control sequence counter
    'notificationtemplate', 'notificationoutbox', 'notificationtask',
    'escalationpolicy', 'escalationstep', 'escalationinstance',
    # Per-tenant access record. Rows are signal-maintained projections of
    # home-tenant + UserRole (see services.core.tenant_membership.ensure_*);
    # there is no membership CRUD endpoint. Adding an operator is gated by
    # role/user perms, and suspend/reactivate by the User viewset's
    # bulk-activate action — never by membership CRUD perms.
    'tenantmembership',
}

# change_/delete_ never granted to ANY role — append-only audit/evidence
# records. Several are also enforced by the immutability DB triggers
# (setup_audit_triggers); this asserts the grant side of that intent.
IMMUTABLE_MODELS = {
    'permissionchangelog', 'capastatustransition', 'recordedit',
    'stepexecutionmeasurement', 'samplingdecision', 'samplingtriggerstate',
    # Z1.4 runtime severity state: mutated ONLY by the switching engine
    # (services.qms.severity_switching.update_after_lot); the API is read-only.
    'samplingseveritystate',
    # Z1.4 runtime severity state: mutated ONLY by the switching engine
    # (services.qms.severity_switching.update_after_lot); the API is read-only.
    'samplingseveritystate',
    # DB-trigger-immutable tables whose change_/delete_ grants were dead
    # (the trigger raises for everyone, superusers included):
    'steptransitionlog', 'samplingauditlog', 'equipmentusage',
    'approvalresponse',
    # A shift-note acknowledgment is a one-time receipt written by the
    # acknowledge action; never edited or deleted via a role's CRUD.
    'shiftnoteack',
    # Engine-managed audit record: StepGateFiring is created (+ its actions_taken
    # updated) by services.qms.quality_gate.evaluate_step_gate, never via a role's
    # CRUD. view_ is granted (STAFF_VIEW_PERMISSIONS); add/change/delete are not.
    'stepgatefiring',
}

# add_ is performed by services / the runtime, never via a role's CRUD.
# (stepexecutionmeasurement is NOT here: operators record measurements over
# HTTP via the bulk-record endpoint, so add_ is granted; change_/delete_
# stay immutable above. equipmentusage/approvalresponse add_ likewise stay
# granted — INSERT is allowed, mutation is not.)
SYSTEM_WRITTEN_MODELS = {
    'permissionchangelog', 'capastatustransition', 'recordedit',
    'samplingdecision', 'samplingtriggerstate', 'samplingseveritystate',
    'steptransitionlog', 'samplingauditlog',
    'stepgatefiring',   # created by the quality-gate engine, not via role CRUD
    'shiftnoteack',     # written by the acknowledge action, not via role CRUD
}

# Granted to NO role as deliberate policy (not a gap to burn down). Maps
# codename -> reason.
WITHHELD_PERMS = {
    # A license to self-approve — the exact thing SOD_APPROVAL_PERMISSIONS
    # exists to prevent. Tenants wanting it can grant it manually, eyes open.
    'approve_own_qualityreports':
        'self-approval bypasses segregation of duties',
    # DocumentLink rows are immutable associations: created by attach
    # (add_documentlink) and removed by detach (delete_documentlink), never
    # edited. There is no change endpoint, so the perm is granted to no role.
    'change_documentlink':
        'links are immutable; managed via attach (add) / detach (delete) only',
}

# delete_ intentionally not granted — these soft-delete / void, or hard-delete
# is disabled (SecureModel.hard_delete raises). Records are retired, not destroyed.
SOFT_DELETE_MODELS = {
    'workorderhold', 'steprollback', 'batchrollback', 'stepoverride',
    'fpirecord', 'qualityreportequipment', 'qualityreportpersonnel',
    'batchexecution', 'steprequirement', 'outsideprocessshipment',
    'milestone', 'milestonetemplate',
    'lifelimitdefinition', 'parttypelifelimit', 'lifetracking',
    'notificationrule', 'notificationschedule',
    # Supplier quality / part approval: records are retired via status
    # (SUSPENDED/DISQUALIFIED/EXPIRED), and re-qualification creates a new row —
    # history is preserved, never hard-deleted.
    'supplierqualification', 'partapproval',
    # Shift notes soft-delete via void (retract); retract is gated by
    # change_shiftnote, not delete_shiftnote.
    'shiftnote',
}

# Burn-down: operational perms that SHOULD be granted to roles but aren't yet.
# Goal: empty. Each removal pairs with a grant in presets.py.
#
# BURNED DOWN: the original 62 operational gaps were granted to all internal
# staff groups via the shared sets in `presets.py` (`STAFF_VIEW_PERMISSIONS`,
# `STAFF_OPERATIONAL_WRITE`, ...; Customer and the '__all__' System Admin
# excluded). New gaps that surface here should be added to the right shared
# set (for broad internal access) or to a specific group, then this set stays
# empty.
KNOWN_GAPS = set()


def _granted_codenames():
    """Codenames granted by at least one EXPLICIT preset group. System Admin
    ('__all__') is skipped — the point is coverage by a role OTHER than the
    catch-all admin."""
    granted = set()
    for preset in GROUP_PRESETS.values():
        perms = preset.get('permissions')
        if perms == '__all__':
            continue
        granted.update(perms)
    return granted


def _is_intentionally_ungranted(codename, model):
    if model in ADMIN_ONLY_MODELS:
        return True
    if codename.startswith(('change_', 'delete_')) and model in IMMUTABLE_MODELS:
        return True
    if codename.startswith('add_') and model in SYSTEM_WRITTEN_MODELS:
        return True
    if codename.startswith('delete_') and model in SOFT_DELETE_MODELS:
        return True
    if codename in WITHHELD_PERMS:
        return True
    return codename in KNOWN_GAPS


class PermissionCoverageGuardTest(TestCase):
    def test_every_permission_is_granted_or_opted_out(self):
        granted = _granted_codenames()
        perms = {
            p.codename: p.content_type.model
            for p in Permission.objects.filter(content_type__app_label='Tracker')
        }
        orphaned = {c for c in perms if c not in granted}

        unexplained = sorted(
            c for c in orphaned if not _is_intentionally_ungranted(c, perms[c])
        )
        self.assertFalse(
            unexplained,
            "\nPermissions granted to no preset group and not opted out — a "
            "tenant user reaching these gets a 403.\nGrant each in "
            "Tracker/presets.py, or add a reasoned opt-out (a *_MODELS rule or "
            "KNOWN_GAPS) in this test:\n  " + "\n  ".join(unexplained),
        )

        stale_gaps = sorted(c for c in KNOWN_GAPS if c not in orphaned)
        self.assertFalse(
            stale_gaps,
            "\nThese KNOWN_GAPS are now granted (or no longer exist) — remove "
            "them from KNOWN_GAPS (burn-down working):\n  "
            + "\n  ".join(stale_gaps),
        )

    def test_every_preset_codename_exists(self):
        """The inverse guard: a granted codename matching no Permission row is
        silently dropped by seeding (codename__in filter), so the grant never
        materializes — e.g. the phantom 'tenantgroupmembership' perms that
        lived in the tenant_admin preset for months."""
        from Tracker.presets import validate_presets

        missing = validate_presets()
        self.assertFalse(
            missing,
            "\nThese preset codenames match no Permission in the database — "
            "typo or removed model? Seeding drops them silently:\n  "
            + "\n  ".join(missing),
        )
