# UQMES

**Product & context:**
- Product is **UQMES**. Paths say "Ambac" / "AmbacTracker" — that's the reference customer. Don't propose renaming work.
- Integration framework lives at `PartsTracker/integrations/`. `Tracker/integrations/` is deleted; don't reference it.
- `django-auditlog` tracks model changes. Don't propose new models for audit-trail reasons.
- Parallel sessions active: Reports, Labels & Scanning, Versioning Architecture. Don't modify files in those areas without confirmation.

**Architecture (applies to new code regardless of existing violations):**
- **`SecureModel`, `SecureManager`, `SecureQuerySet`, `TenantMiddleware`, and migration `0033_enable_rls.py` are load-bearing for tenant isolation.** Modifications require explicit intent — confirm before editing.
- **Business logic does not live in `save()`.** Auto-fill fields (sequence numbers, timestamps) are acceptable; state transitions, cross-aggregate writes, and validations that query other models are not.
- **Model methods are `@property` accessors and `__str__`.** Anything that queries other aggregates, mutates related records, or implements a state machine belongs in a service.
- **New tenant-scoped models must inherit `SecureModel`.**
- **Scope queries by tenant.** Every query includes `tenant=`, `.for_user(user)`, or `.for_tenant(t)`. No exceptions. (Rule changes when auto-scoping ships.)
- **Versioned models mutate via `create_new_version()`.** Never bypass with raw `.save()`. See `Documents/VERSIONING_ARCHITECTURE.md` for categorization.
- **Soft-delete with `VoidableModel.void()`**, not hard-delete. Preserves audit trail.
- **DTOs are frozen dataclasses.** No Pydantic for internal data flow. DRF serializers stay at the HTTP boundary only.
- **Celery tasks take IDs and primitives, not model instances.** Signature is `(id, tenant_id, ...)` with JSON-serializable args. Tasks re-fetch via repo.
- **After changing any file in `serializers/` or `viewsets/`, regenerate `schema.yaml` and commit in the same PR.** Frontend types depend on it.

**Default choices:**
- **Prefer fields over new tables.** Status enums, nullable FKs, and flags on existing models beat new tables. New tables only for genuinely new aggregates.
- **Prefer minimum-viable over textbook-correct.** Don't propose tooling (linters, DI containers, schema frameworks) unless a specific named problem requires it.

**Process:**
- **Opportunistic refactor:** scope changes to files already touched. Commit refactors separately from features. Ask before deleting files or top-level symbols.
- **Communication:** incorporate corrections without preamble. "Fair pushback" / "good catch" / "I was wrong" are noise when the correction is straightforward.

**Commands:**
- Run tests: `cd PartsTracker && python manage.py test`
- Regenerate API schema: `cd PartsTracker && python manage.py spectacular --file schema.yaml`
- Regenerate frontend types: `cd ambac-tracker-ui && bun run generate-api`
- Typecheck frontend (after type regen): `cd ambac-tracker-ui && bun run typecheck`
- Apply migrations: `cd PartsTracker && python manage.py migrate`
- Seed dev/demo data: `cd PartsTracker && python manage.py seed_demo` (or `seed_dev`)
