"""Dead-endpoint guard: every exposed API action must be reachable by at least
one real (non-System-Admin) role.

`test_permission_coverage` checks the GRANT side: every permission is granted
to some role or explicitly opted out. But nothing cross-checked the opt-outs
against what the API actually exposes — which is how the calendar models ended
up in SOFT_DELETE_MODELS ("delete is intentionally ungranted") while their
viewsets exposed DELETE and the calendar UI shipped delete buttons that 403'd
for everyone.

This test closes that gap from the EXPOSURE side. It walks the resolved URL
conf, finds every DRF viewset route (all routers — main, reports,
integrations), computes the permission set `TenantModelPermissions` will
demand for each exposed action, and asserts some preset role other than
System Admin ('__all__') holds all of them. An endpoint no real role can ever
use is either a bug (missing grant) or dead surface (should not be routed) —
both belong in ALLOWED_UNREACHABLE with a written justification, or fixed.

No DB: presets and the URL conf are plain Python.
"""

from django.test import SimpleTestCase
from django.urls import get_resolver

from Tracker.permissions import RequirePermission, TenantModelPermissions
from Tracker.presets import GROUP_PRESETS

# (viewset class name, action) pairs that are intentionally unreachable by any
# non-System-Admin role. Every entry needs a justification — this list is the
# exposure-side twin of test_permission_coverage's opt-out sets, and the same
# rule applies: keep it shrinking. Deliberately per-route (not derived from
# those opt-out sets): deriving would re-open the blindness this test exists
# to close — a model opted out as "soft-delete" while its viewset exposes
# DELETE and the UI ships a delete button (the calendar-models bug). None of
# the routes below has a frontend caller (verified 2026-09-01); if a UI grows
# one, remove the entry and grant the perm instead.
ALLOWED_UNREACHABLE = {
    # Immutable evidence records — change/delete never granted by design
    # (IMMUTABLE_MODELS + DB immutability triggers). ModelViewSet boilerplate
    # exposes the writes; the perm gate is what enforces immutability at the
    # API layer.
    ('ApprovalResponseViewSet', 'update'),
    ('ApprovalResponseViewSet', 'partial_update'),
    ('ApprovalResponseViewSet', 'destroy'),
    ('StepExecutionMeasurementViewSet', 'update'),
    ('StepExecutionMeasurementViewSet', 'partial_update'),
    ('StepExecutionMeasurementViewSet', 'destroy'),
    # Retired-not-destroyed records (SOFT_DELETE_MODELS): lifecycle ends via a
    # status transition or void, never a DELETE; no UI issues these.
    ('SupplierQualificationViewSet', 'destroy'),   # retired via suspend/disqualify
    ('PartApprovalViewSet', 'destroy'),            # retired via suspend/disqualify
    ('ShiftNoteViewSet', 'destroy'),               # retracted via change_shiftnote
    ('MilestoneTemplateViewSet', 'destroy'),       # templates archived, not deleted
    ('StepOverrideViewSet', 'destroy'),            # audit trail of an override
    ('FPIRecordViewSet', 'destroy'),               # quality evidence
    ('BatchExecutionViewSet', 'destroy'),          # execution history
    ('OutsideProcessShipmentViewSet', 'destroy'),  # shipment record
}


def _iter_url_patterns(resolver):
    for entry in resolver.url_patterns:
        if hasattr(entry, 'url_patterns'):  # URLResolver — recurse into includes
            yield from _iter_url_patterns(entry)
        else:
            yield entry


def _viewset_routes():
    """Yield (viewset class, http method, action name) for every DRF
    router-generated route in the resolved URL conf."""
    seen = set()
    for pattern in _iter_url_patterns(get_resolver()):
        callback = pattern.callback
        cls = getattr(callback, 'cls', None)
        actions = getattr(callback, 'actions', None)
        if cls is None or not actions:
            continue
        for method, action in actions.items():
            key = (cls, method, action)
            if key not in seen:
                seen.add(key)
                yield cls, method.upper(), action


def _model_name(cls):
    queryset = getattr(cls, 'queryset', None)
    if queryset is not None:
        return queryset.model._meta.model_name
    serializer = getattr(cls, 'serializer_class', None)
    model = getattr(getattr(serializer, 'Meta', None), 'model', None)
    return model._meta.model_name if model is not None else None


def _uses_tenant_model_permissions(cls):
    for perm in getattr(cls, 'permission_classes', []):
        if isinstance(perm, type) and issubclass(perm, TenantModelPermissions):
            return True
    return False


def _required_perms(cls, method, action):
    """Mirror TenantModelPermissions.has_permission's declarative demands for
    one route: CRUD perm from the HTTP method (unless crud-exempt), plus the
    viewset's action_permissions entry, plus any RequirePermission instances
    in permission_classes. Cosign gates are excluded — a cosigner can satisfy
    them at runtime, so they don't make an endpoint unreachable."""
    required = set()
    crud_exempt = getattr(cls, 'crud_exempt_actions', None) or set()
    if action not in crud_exempt:
        model_name = _model_name(cls)
        prefix = TenantModelPermissions.perms_map.get(method)
        if model_name and prefix:
            required.add(f'{prefix}_{model_name}')
    action_permissions = getattr(cls, 'action_permissions', None) or {}
    required.update(action_permissions.get(action) or [])
    for perm in getattr(cls, 'permission_classes', []):
        if isinstance(perm, RequirePermission):
            required.update(perm.required_perms)
    return required


class DeadEndpointGuardTest(SimpleTestCase):
    def test_every_endpoint_is_reachable_by_a_real_role(self):
        role_perms = {
            key: set(preset['permissions'])
            for key, preset in GROUP_PRESETS.items()
            if preset['permissions'] != '__all__'
        }

        failures = []
        used_allowlist = set()
        for cls, method, action in _viewset_routes():
            if not _uses_tenant_model_permissions(cls):
                continue  # gated by other means (custom classes, AllowAny, ...)
            required = _required_perms(cls, method, action)
            if not required:
                continue
            reachable = any(required <= perms for perms in role_perms.values())
            if (cls.__name__, action) in ALLOWED_UNREACHABLE:
                if not reachable:  # a reachable entry is stale, not "used"
                    used_allowlist.add((cls.__name__, action))
                continue
            if not reachable:
                failures.append(
                    f"{cls.__name__}.{action} ({method}) requires {sorted(required)} "
                    f"— no non-System-Admin role holds all of these"
                )

        self.assertFalse(
            failures,
            "Dead endpoints — exposed API actions no real role can use.\n"
            "Fix: grant the perm in presets.py, stop exposing the action, or add\n"
            "(ViewSet, action) to ALLOWED_UNREACHABLE with a justification:\n  "
            + "\n  ".join(sorted(failures))
        )

        # An allowlist entry whose route no longer exists is stale — remove it
        # so the list can only shrink alongside the actual API surface.
        stale = ALLOWED_UNREACHABLE - used_allowlist
        self.assertFalse(
            stale,
            f"Stale ALLOWED_UNREACHABLE entries (route gone or now reachable): {sorted(stale)}"
        )
