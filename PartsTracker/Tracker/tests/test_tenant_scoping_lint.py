"""
Lint test — flags ORM queries on tenant-scoped models that don't have
explicit tenant scoping.

The test walks every .py file in Tracker/ and integrations/, finds
direct `Model.objects.<method>(...)` calls on models that have a
`tenant` FK, and fails if the surrounding context doesn't show
tenant scoping (`tenant=`, `.for_user(...)`, `.for_tenant(...)`, or
an FK-scoped kwarg like `step=...`).

Rationale: the default `.objects` manager on tenant-scoped models
returns cross-tenant data. The codebase uses `.for_user(user)` /
`.for_tenant(tenant)` as an opt-in tenant filter, but forgetting
that call is a silent security hole. This test makes the forgetting
loud at CI time.

HOW TO FIX A FLAGGED LINE:

1. **Add explicit tenant scoping** (preferred):
       MeasurementDefinition.objects.filter(id=x, tenant=tenant).exists()
       # or
       MeasurementDefinition.objects.for_user(request.user).filter(id=x)

2. **If the query is implicitly tenant-scoped via an FK** (e.g., you
   already have a tenant-scoped Step instance and filter Parts by it),
   the test should pass automatically — FK kwargs like `step=`, `work_order=`,
   `part=`, `order=`, `process=` are recognized as FK-scoped.

3. **If the query is legitimately cross-tenant** (e.g., admin code,
   data migration), add an inline comment explaining why:
       User.objects.filter(email=x)  # tenant-safe: lookup by globally unique email

4. **If a whole file is inherently safe** (data migration, management
   command, test fixture), add its path to `ALLOWED_PATH_PATTERNS`.
"""

import io
import re
import tokenize
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase


class TenantScopingLintTests(SimpleTestCase):
    """
    Detects direct `Model.objects.*` queries on tenant-scoped models
    that lack tenant scoping.
    """

    # --- Configuration --------------------------------------------------

    # Models to exclude even though they have a `tenant` FK. These are
    # models where cross-tenant queries are intentional:
    #   - Tenant itself (would be circular)
    #   - User (users can legitimately belong to multiple tenants via
    #     UserRole; email is globally unique)
    EXCLUDED_MODEL_NAMES = frozenset({
        "Tenant",
        "User",
    })

    # Paths where raw Model.objects access is acceptable. Expressed as
    # substrings of the POSIX-style relative path. Keep the list small
    # and justify each entry with a comment.
    ALLOWED_PATH_PATTERNS = (
        "/migrations/",              # data migrations run across tenants
        "/migrations_backup/",       # same, historical
        "/tests/",                   # tests create multi-tenant fixtures
        "/management/commands/",     # admin-run scripts, no web context
        "/admin.py",                 # Django admin is superuser-only
        "Tracker/views.py",          # legacy Django views being phased out
        "/viewsets/base.py",         # defines TenantScopedMixin itself
        "/presets.py",               # seeds default groups across tenants
        "/groups.py",                # tenant group bootstrap helpers
        "/backends.py",              # auth backend, needs cross-tenant lookup
        "test_tenant_scoping_lint.py",  # this file's own patterns
    )

    # If a line (or the 5 lines following a query) contains any of these
    # substrings, the query is considered tenant-safe.
    SAFE_TENANT_MARKERS = (
        "tenant=",
        "tenant_id=",
        "tenant__",
        ".for_user(",
        ".for_tenant(",
        "filter_by_tenant(",
        "tenant_context(",
        "get_tenant_for_object(",
        "set_tenant_context(",
        # DRF field/filter queryset kwargs: these are used for input
        # validation and relational lookups. Cross-tenant lookup is
        # prevented by PostgreSQL Row-Level Security (see ENABLE_RLS and
        # Tracker/utils/tenant_context.py). Flagging every occurrence
        # creates noise without surfacing real bugs.
        "PrimaryKeyRelatedField(",
        "SlugRelatedField(",
        "HyperlinkedRelatedField(",
        "ModelChoiceFilter(",
        "ModelMultipleChoiceFilter(",
        "ModelChoiceField(",
        "ModelMultipleChoiceField(",
        # Self-lookup: `Model.objects.get(pk=self.pk)` inside a model
        # method re-fetches the current instance. Since `self` is already
        # tenant-scoped (UUID/autofield PKs don't collide across tenants)
        # this is effectively a no-op round-trip.
        "pk=self.pk",
        "pk=self.id",
        "id=self.id",
        "id=self.pk",
        "# tenant-safe:",
        "# lint-ignore: tenant",
    )

    # Substrings indicating the file is a DRF viewset/view that uses
    # TenantScopedMixin or an equivalent base class which overrides
    # get_queryset() to apply tenant scoping. When present, a bare
    # `queryset = Model.objects.all()` class attribute is safe.
    TENANT_SCOPED_BASE_MARKERS = (
        "TenantScopedMixin",
        "TenantFilterMixin",
    )

    # Query methods to check. Anything that reads or writes.
    # Note: `bulk_update` is intentionally omitted — it operates on a
    # list of already-fetched model instances, so tenant scoping is
    # carried by the objects themselves (the first positional arg).
    QUERY_METHODS = (
        "filter", "get", "all", "exists", "count",
        "first", "last", "exclude",
        "values", "values_list", "aggregate", "annotate",
        "update", "delete",
        "create", "get_or_create", "update_or_create",
        "bulk_create",
    )

    # FK field names that, when used as the first kwarg to a query
    # method, imply tenant scoping via the FK relationship. If the
    # parent model is tenant-scoped and you're filtering by it, the
    # child rows are constrained to that tenant too.
    FK_SCOPE_FIELD_NAMES = (
        "work_order", "order", "orders",
        "step", "steps", "step_execution", "step_executions",
        "part", "parts", "part_type", "part_types",
        "process", "processes", "process_step",
        "measurement", "measurement_definition",
        "integration",
        "company", "companies",
        "capa",
        "document", "documents",
        "milestone", "milestone_template",
        "work_center", "facility",
        "equipment", "equipments",
        "training_type", "training_record",
        "execution",
        "quality_report", "sampling_ruleset", "sampling_rule",
        "approval", "approval_request",
        "report", "rca_record", "rca",
    )

    # --- Helpers --------------------------------------------------------

    @classmethod
    def _tenant_scoped_models(cls):
        """
        Discover every model in installed apps that has a FK to Tenant.
        """
        scoped = set()
        for model in apps.get_models():
            if model.__name__ in cls.EXCLUDED_MODEL_NAMES:
                continue
            for field in model._meta.get_fields():
                related = getattr(field, "related_model", None)
                if related is not None and related.__name__ == "Tenant":
                    scoped.add(model.__name__)
                    break
        return scoped

    def _build_query_regex(self, model_names):
        """
        Compile a regex that matches `ModelName.objects.METHOD(` *or*
        `ModelName.all_objects.METHOD(` for any of the given model names.

        ``all_objects`` is a SecureModel manager that deliberately bypasses
        the soft-delete and tenant filters — used to bootstrap tenant
        context in Celery tasks. Its legitimate uses are always paired
        with a ``tenant_context(...)`` wrap nearby, so they pass the
        safety check; misuses surface as failures.
        """
        model_alternation = "|".join(
            re.escape(name) for name in sorted(model_names, key=len, reverse=True)
        )
        method_alternation = "|".join(self.QUERY_METHODS)
        manager_alternation = r"(?:objects|all_objects)"
        pattern = (
            rf"\b({model_alternation})\.{manager_alternation}"
            rf"\.({method_alternation})\("
        )
        return re.compile(pattern)

    def _build_fk_scoped_regex(self):
        """
        Compile a regex that matches any FK-scoped kwarg appearing in a
        query call context. Handles:
            .objects.filter(work_order=wo, ...)              # first kwarg
            .objects.create(name=..., part_type=self.pt)     # later kwarg
            .objects.filter(process_steps__step=self)        # FK chain
            .objects.filter(                                 # multi-line
                step=self,
                ...
            )
        The kwarg must be preceded by a boundary (``(``, ``,``, whitespace)
        so that unrelated identifiers don't match. The ``__FIELD=`` form
        catches cross-FK chain lookups (the final segment of the path is
        what constrains the tenant).
        """
        fk_alternation = "|".join(self.FK_SCOPE_FIELD_NAMES)
        # Matches `FIELD=`, `FIELD_id=`, or `...__FIELD=` as a kwarg,
        # with a preceding boundary character so that unrelated
        # identifiers (e.g. `last_order=`) don't accidentally match.
        pattern = rf"(?:[(,\s]|__)(?:{fk_alternation})(?:_id)?\s*="
        return re.compile(pattern)

    def _is_path_allowed(self, posix_path):
        return any(p in posix_path for p in self.ALLOWED_PATH_PATTERNS)

    def _context_is_safe(self, context, full_line, preceding, file_text):
        """
        Decide whether a query-with-context is tenant-safe.

        `context` is the source text starting at the query call and
        extending up to 5 lines forward (covers multi-line kwargs).
        `full_line` is the entire line containing the query (so that
        markers appearing *before* the query, e.g.
        ``self.filter_by_tenant(X.objects.all())``, are detected).
        `file_text` is the full file source (used to detect whether the
        file is a tenant-scoped viewset/filter module).
        """
        combined = preceding + full_line + "\n" + context
        if any(marker in combined for marker in self.SAFE_TENANT_MARKERS):
            return True
        if self._fk_scoped_regex.search(context):
            return True
        # Class-attribute `queryset = Model.objects.all()` pattern in
        # files that use TenantScopedMixin / TenantFilterMixin. The mixin
        # overrides get_queryset() to apply tenant scoping, so the raw
        # queryset class attribute is never used cross-tenant at runtime.
        stripped = full_line.lstrip()
        if stripped.startswith("queryset ") or stripped.startswith("queryset="):
            if any(m in file_text for m in self.TENANT_SCOPED_BASE_MARKERS):
                return True
        return False

    def _extract_context(self, text, match_start, max_lines=10):
        """
        Return the substring of `text` starting at `match_start` and
        spanning up to `max_lines` lines forward.
        """
        cursor = match_start
        for _ in range(max_lines):
            next_newline = text.find("\n", cursor)
            if next_newline == -1:
                return text[match_start:]
            cursor = next_newline + 1
        return text[match_start:cursor]

    def _extract_full_line(self, text, match_start):
        """Return the entire line of `text` that contains match_start."""
        line_start = text.rfind("\n", 0, match_start) + 1
        line_end = text.find("\n", match_start)
        if line_end == -1:
            line_end = len(text)
        return text[line_start:line_end]

    def _extract_preceding_lines(self, text, match_start, max_lines=2):
        """
        Return up to `max_lines` lines of `text` immediately preceding
        the line containing match_start. Used to detect wrapping
        constructs like ``serializers.PrimaryKeyRelatedField(\\n`` where
        the safety marker is on a line above the actual query.
        """
        line_start = text.rfind("\n", 0, match_start) + 1
        cursor = line_start
        for _ in range(max_lines):
            prev_newline = text.rfind("\n", 0, cursor - 1)
            if prev_newline == -1:
                cursor = 0
                break
            cursor = prev_newline + 1
        return text[cursor:line_start]

    def _compute_skip_ranges(self, text):
        """
        Return a list of (start_offset, end_offset) ranges in `text`
        that correspond to Python comments and string literals (including
        docstrings). Matches inside these ranges are ignored — they are
        not executable code.

        Returns an empty list if the file can't be tokenized cleanly
        (syntax errors, etc.), which means nothing is skipped and the
        regex pass runs as before.
        """
        # Build a prefix-sum index: line_offsets[i] = byte offset of the
        # start of line (i+1). tokenize reports 1-indexed line numbers.
        line_offsets = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                line_offsets.append(i + 1)

        def pos_to_offset(row, col):
            # row is 1-indexed; offset of line start + column byte offset
            if row - 1 >= len(line_offsets):
                return len(text)
            return line_offsets[row - 1] + col

        ranges = []
        try:
            tokens = tokenize.generate_tokens(io.StringIO(text).readline)
            for tok in tokens:
                if tok.type in (tokenize.COMMENT, tokenize.STRING):
                    start = pos_to_offset(tok.start[0], tok.start[1])
                    end = pos_to_offset(tok.end[0], tok.end[1])
                    ranges.append((start, end))
        except (tokenize.TokenizeError, IndentationError, SyntaxError):
            return []
        return ranges

    @staticmethod
    def _offset_in_ranges(offset, ranges):
        """Binary-search whether `offset` falls inside any (start, end)."""
        lo, hi = 0, len(ranges)
        while lo < hi:
            mid = (lo + hi) // 2
            start, end = ranges[mid]
            if offset < start:
                hi = mid
            elif offset >= end:
                lo = mid + 1
            else:
                return True
        return False

    # --- The test --------------------------------------------------------

    def setUp(self):
        self._fk_scoped_regex = self._build_fk_scoped_regex()

    def test_no_unscoped_tenant_model_queries(self):
        base_dir = Path(settings.BASE_DIR)
        scan_roots = [
            base_dir / "Tracker",
            base_dir / "integrations",
        ]

        tenant_models = self._tenant_scoped_models()
        self.assertTrue(
            tenant_models,
            "Failed to discover any tenant-scoped models. Check that "
            "Django apps are loaded and Tenant model exists.",
        )

        query_regex = self._build_query_regex(tenant_models)

        violations = []

        for root in scan_roots:
            if not root.exists():
                continue

            for py_file in root.rglob("*.py"):
                relative = py_file.relative_to(base_dir).as_posix()

                if self._is_path_allowed(relative):
                    continue

                try:
                    text = py_file.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue

                skip_ranges = self._compute_skip_ranges(text)

                for match in query_regex.finditer(text):
                    # Ignore hits inside comments or string literals /
                    # docstrings — those are not executable ORM calls.
                    if self._offset_in_ranges(match.start(), skip_ranges):
                        continue

                    context = self._extract_context(text, match.start())
                    full_line = self._extract_full_line(text, match.start())
                    preceding = self._extract_preceding_lines(text, match.start())

                    if self._context_is_safe(context, full_line, preceding, text):
                        continue

                    line_number = text[: match.start()].count("\n") + 1
                    # The offending line itself (first line of context)
                    first_line = context.splitlines()[0].strip()

                    violations.append(
                        f"{relative}:{line_number}\n    {first_line}"
                    )

        if violations:
            self.fail(self._format_failure(violations, len(tenant_models)))

    # --- Structural test: default manager must expose tenant scoping ----

    # Methods a SecureManager-compatible manager must expose. If a model
    # has a `tenant` FK but its default manager is missing any of these,
    # cross-tenant queries become the silent default for that model
    # (Model.objects.all() returns all tenants' rows). This is exactly
    # how EquipmentManager/CalibrationRecordManager silently overrode
    # SecureManager and created a cross-tenant bypass.
    REQUIRED_MANAGER_METHODS = ("for_user", "active")

    # Tenant-scoped models whose default manager legitimately lacks the
    # SecureManager API. Keep this list short; each entry is a known
    # exception that has been reviewed.
    MANAGER_EXEMPT_MODEL_NAMES = frozenset({
        # Add model names here with an inline comment explaining why the
        # default manager can safely skip the SecureManager interface.
    })

    def test_secure_model_subclasses_keep_secure_default_manager(self):
        """
        Every ``SecureModel`` subclass must keep a default manager that
        exposes the ``SecureManager`` interface (``.for_user``, ``.active``).

        The common trap: adding a custom manager for domain-specific
        query shortcuts (``EquipmentManager.operational()``, etc.) and
        inheriting from ``models.Manager`` instead of ``SecureManager``.
        This silently replaces the inherited ``SecureManager``, so
        ``Model.objects.all()`` returns cross-tenant data and
        ``Model.objects.for_user(user)`` raises ``AttributeError``.

        Fix by inheriting from ``SecureManager`` / ``SecureQuerySet``:

            class FooQuerySet(SecureQuerySet):    # not models.QuerySet
                ...
            class FooManager(SecureManager):      # not models.Manager
                def get_queryset(self):
                    return FooQuerySet(self.model, using=self._db)

        If a specific ``SecureModel`` subclass legitimately needs a
        non-``SecureManager`` default manager, add it to
        ``MANAGER_EXEMPT_MODEL_NAMES`` with a comment explaining why.
        """
        from Tracker.models.core import SecureModel

        failures = []
        for model in apps.get_models():
            if model.__name__ in self.EXCLUDED_MODEL_NAMES:
                continue
            if model.__name__ in self.MANAGER_EXEMPT_MODEL_NAMES:
                continue
            if not issubclass(model, SecureModel):
                continue

            manager = model._default_manager
            missing = [
                m for m in self.REQUIRED_MANAGER_METHODS
                if not hasattr(manager, m)
            ]
            if missing:
                module = model.__module__
                manager_cls = type(manager).__name__
                failures.append(
                    f"{module}.{model.__name__} (default manager: "
                    f"{manager_cls}) is missing: {', '.join(missing)}"
                )

        if failures:
            self.fail(
                "\nSecureModel subclasses must use a SecureManager-compatible "
                "default manager.\n"
                "\n"
                "Defining a custom manager that inherits from models.Manager "
                "(instead of\n"
                "SecureManager) silently replaces the inherited tenant "
                "scoping — so\n"
                "Model.objects.all() will return cross-tenant data without "
                "warning.\n"
                "\n"
                "Fix by inheriting from SecureManager / SecureQuerySet:\n"
                "\n"
                "    class FooQuerySet(SecureQuerySet):  # not models.QuerySet\n"
                "        ...\n"
                "    class FooManager(SecureManager):    # not models.Manager\n"
                "        def get_queryset(self):\n"
                "            return FooQuerySet(self.model, using=self._db)\n"
                "\n"
                "Domain-specific query methods on the custom queryset/manager "
                "keep working\n"
                "unchanged (they only call self.filter()/self.get_queryset()).\n"
                "\n"
                "If this model legitimately needs to skip SecureManager, add "
                "it to\n"
                "MANAGER_EXEMPT_MODEL_NAMES with an inline comment explaining "
                "why.\n"
                "\n"
                "Offenders:\n  " + "\n  ".join(failures)
            )

    def _format_failure(self, violations, tenant_model_count):
        header = (
            f"\n{len(violations)} potentially unscoped tenant-model "
            f"quer{'y' if len(violations) == 1 else 'ies'} found "
            f"across {tenant_model_count} tenant-scoped models.\n"
            "\n"
            "Each flagged line uses `Model.objects.<method>(...)` on a\n"
            "model with a `tenant` FK, without an obvious tenant filter.\n"
            "\n"
            "To fix:\n"
            "  1. Add tenant scoping:\n"
            "       Model.objects.filter(..., tenant=tenant)\n"
            "       Model.objects.for_user(user).filter(...)\n"
            "       Model.objects.for_tenant(tenant).filter(...)\n"
            "  2. Or, if already scoped via an FK (e.g., step=step),\n"
            "     add `step` (or whatever field) to FK_SCOPE_FIELD_NAMES.\n"
            "  3. Or, if legitimately cross-tenant, add an inline comment:\n"
            "       Model.objects.filter(x)  # tenant-safe: <reason>\n"
            "\n"
            "Violations:\n"
        )
        return header + "\n\n".join(violations)
