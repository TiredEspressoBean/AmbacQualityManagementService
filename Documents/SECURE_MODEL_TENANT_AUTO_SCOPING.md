# SecureModel Auto-Tenant-Scoping

**Last Updated:** April 2026
**Status:** Note for future work — not started
**Context:** This belongs to the parallel tenant-scoping-hardening
workstream (see the other CC session's prompt), but the key insight
is recorded here so it doesn't get lost.

---

## The idea in one sentence

Rather than introducing a new `TenantScopedModel` class alongside the
existing `SecureModel`, **enhance `SecureModel`'s default manager to
auto-filter by the current tenant from a `contextvars.ContextVar`**.
Every model that currently inherits `SecureModel` gets default-safe
tenant scoping for free, with zero per-model migration.

---

## Background

The codebase currently uses an **opt-in** tenant-scoping pattern:

```python
Orders.objects.for_user(user)       # tenant-scoped
Orders.objects.for_tenant(tenant)   # tenant-scoped
Orders.objects.filter(id=x)         # NOT scoped — returns all tenants
```

Forgetting `.for_user()` or `.for_tenant()` is a silent security
failure. A lint test (`Tracker/tests/test_tenant_scoping_lint.py`) was
added to catch this at CI time, and it did find six real instances
during its first run — all fixed. The lint is necessary but reactive.

The long-term fix is structural: make the default queryset
tenant-scoped so forgetting becomes a hard error (missing context)
instead of a silent leak (cross-tenant data returned).

---

## Why not a separate `TenantScopedModel` class

An earlier draft of this plan proposed a new abstract class
`TenantScopedModel` that models would inherit from. That approach has
real downsides for this codebase:

| | Separate `TenantScopedModel` | Enhance `SecureModel` |
|--|---|---|
| Models to migrate | Every tenant-scoped model inherits a new class | Zero — inheritance is already in place |
| Class hierarchy | Two bases; pick wisely per model | Single base |
| Risk of forgetting | Yes — add new model, forget to inherit | No — if it's a `SecureModel`, it's scoped |
| Disruption | Two codepaths during transition | One refactor, everything changes at once |
| Fit to Ambac QMS | Over-abstracted; not enough models to justify | Matches what you actually have |

`SecureModel` is already the universal base for tenant-scoped models
in this codebase. Every `Orders`, `Parts`, `QualityReports`,
`QuarantineDisposition`, `Processes`, etc. inherits from it and has a
`tenant` FK. Folding auto-scoping into `SecureModel` directly is the
minimum-friction change.

---

## The concrete change

In `Tracker/models/core.py`:

```python
from contextvars import ContextVar
from django.db import models

# (Probably already exists in Tracker/utils/tenant_context.py as
#  a contextvar — re-use that one.)
_current_tenant: ContextVar = ContextVar("current_tenant", default=None)


class SecureQuerySet(models.QuerySet):
    """
    Keep all existing methods: .for_user(), .for_tenant(), .active(),
    etc. They continue to work and compose cleanly on top of an
    already-tenant-scoped base queryset.
    """
    ...


class SecureManager(models.Manager):
    def get_queryset(self):
        qs = SecureQuerySet(self.model, using=self._db)
        tenant = _current_tenant.get()
        if tenant is not None:
            qs = qs.filter(tenant=tenant)
        return qs


class SecureModel(models.Model):
    # ... existing fields ...

    objects = SecureManager()
    all_tenants = models.Manager()   # explicit escape hatch

    class Meta:
        abstract = True
```

### Companion middleware change

`TenantMiddleware` should `.set()` the contextvar at request start
(in addition to its current behavior of setting
`request.user._current_tenant`):

```python
# In TenantMiddleware.__call__(), after tenant resolution:
token = _current_tenant.set(tenant)
try:
    response = self.get_response(request)
finally:
    _current_tenant.reset(token)
```

Celery tasks already use `Tracker/utils/tenant_context.py`'s
`tenant_context(tenant_id)` context manager, which can be updated to
set the same contextvar.

---

## Prerequisites — audit SecureModel subclasses

**Critical:** before flipping on auto-scoping, verify every `SecureModel`
subclass actually has a `tenant` FK. If there's a `SecureModel` subclass
that doesn't (a global lookup table that shouldn't be tenant-scoped),
the auto-filter will raise `FieldError` when it tries to filter.

Audit command:

```bash
cd PartsTracker
grep -l "class.*SecureModel" Tracker/models/*.py | \
  xargs grep -L "tenant = models\.ForeignKey"
```

Any files listed are subclasses of `SecureModel` that lack a
tenant FK. Three ways to resolve:

1. **Add a `tenant` FK** to the straggler model (most likely right
   for this codebase — nothing should really be "global" at this
   scale).
2. **Keep it non-tenant-scoped** but stop inheriting from `SecureModel` —
   use `models.Model` directly, or introduce a
   `SecureModelBase` abstract class for the non-tenant fields and
   have `SecureModel` add tenant FK + auto-scoping on top.
3. **Introduce a narrower intermediate class** — `TenantSecureModel`
   that adds the manager only for the subset of SecureModels that
   have tenant scoping. (This is the "separate class" approach in
   disguise; avoid unless option 1 is genuinely wrong.)

Most codebases find 95%+ of `SecureModel` subclasses already have a
tenant FK. If that's the case here, option 1 for any stragglers is
the right move.

---

## Interaction with existing `.for_user()` / `.for_tenant()`

These methods don't go away. They do more than tenant scoping:
permission filtering, Order-relationship filtering, archived
exclusion, etc. With the new auto-scoping:

- `Orders.objects.filter(id=x)` — tenant-scoped by default
- `Orders.objects.for_user(user).filter(id=x)` — tenant-scoped + permission-filtered + relationship-filtered

`.for_user()` becomes a **composer**: it adds permission and
relationship logic on top of the already-scoped base queryset. The
redundant tenant filter it applies internally is harmless (filters
for the same tenant twice).

Viewsets that currently use `.for_user(request.user)` in
`get_queryset()` can continue to do so unchanged, or be simplified
over time. No big-bang migration.

---

## Interaction with existing RLS setup

`ENABLE_RLS` + the migration at
`Tracker/migrations_backup/0033_enable_rls.py` are the database-level
enforcement layer. They stay exactly as designed. RLS enforces at the
storage layer; the auto-scoping manager catches bugs earlier (before
they reach the DB), with clearer error messages, and in dev
environments where RLS is off.

Defense in depth: manager at the ORM layer, RLS at the DB layer,
lint test at the CI layer, code review as the human layer.

---

## Escape hatch: when you actually need to cross tenants

`Model.all_tenants` is the explicit opt-out. Uses include:

- Django admin for superusers
- Data migrations that touch all tenants
- Health checks, monitoring, global metrics
- The `sync_hubspot` management command (one-off admin tooling)
- Tests that create fixtures across tenants

Every use of `.all_tenants` is greppable and obvious in code review.
Contrast with the current pattern where `.objects.filter(...)` looks
fine but is actually dangerous.

---

## Rollout plan (when this work is scheduled)

1. **Audit SecureModel subclasses** for missing tenant FKs. Resolve
   stragglers first.
2. **Add `SecureManager` + `all_tenants` manager** to `SecureModel`.
   At this stage, nothing auto-filters yet — the contextvar is always
   `None`, so the manager behaves exactly like the current one.
3. **Update `TenantMiddleware`** to `.set()` the contextvar on every
   request. `tenant_context()` already does the equivalent for Celery.
4. **Run the full test suite.** Most tests use `TenantTestCase`
   which sets up tenant context — they should pass. Any tests that
   fail are ones that were accidentally relying on cross-tenant
   visibility; fix them case-by-case.
5. **Run `test_tenant_scoping_lint.py`.** The lint test should still
   pass (the manager is strictly additive; explicit `tenant=` filters
   still count as safe).
6. **Simplify callsites over time** — any viewset whose sole reason
   to call `.for_user(user)` was tenant scoping can drop the call.
   Viewsets that need permission or relationship filtering keep it.
7. **Consider deleting the lint test** once the manager is proven
   stable, or keep it as belt-and-suspenders for `.all_tenants` misuse.

---

## Why not now

The Typst reports sprint is in flight. The other CC session is handling
security/tenant scoping in parallel. This is a structural cleanup that
should be its own focused effort, not shoehorned into another project.
Capturing the idea here so it doesn't get lost.

Reasonable timing: after the Typst migration ships (Phase 2 done), if
the lint test starts flagging false positives at an annoying rate, or
if a new class of tenant-scoping bug surfaces. Otherwise, whenever the
next architectural-improvement window opens.
