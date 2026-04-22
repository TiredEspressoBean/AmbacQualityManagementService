"""
Django system checks for Tracker conventions.

Registered from `TrackerConfig.ready()`. Run at `manage.py check` time
(and automatically before `runserver`, `test`, etc.).

Current checks
--------------

**W001 — `SecureModel.save()` must not use `self.pk` to detect new rows.**

    SecureModel assigns a `uuid7` PK at Python-instantiation time (via
    `id = UUIDField(default=uuid7)`), so `self.pk` is ALWAYS populated
    — even on an unsaved row. The following idioms are wrong on a
    SecureModel subclass `save()`:

        if not self.pk:         # always False — never fires on insert
        if self.pk is None:     # always False
        if self.pk:             # always True — fires on update AND insert

    Use `self._state.adding` instead. This is the canonical Django
    check for "is this row being inserted?"

    We found 2 real behavioral bugs from this pattern (Parts sampling
    evaluation never firing on new parts; MaterialUsage lot-quantity
    decrement never firing on consumption). The check prevents
    regression at `manage.py check` time.

    Checks AST-walked from `inspect.getsource(cls.save)`; only fires
    when `save` is defined on the subclass itself (not merely inherited).
"""
from __future__ import annotations

import ast
import inspect

from django.core.checks import Warning, register


_SELF_PK_PATTERNS = (
    "if self.pk:",
    "if not self.pk:",
    "if self.pk is None",
    "if self.pk is not None",
    "self.pk is None",
    "self.pk is not None",
)


def _is_self_pk_attribute(node: ast.AST) -> bool:
    """True for an `Attribute(value=Name('self'), attr='pk')` AST node."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == 'pk'
        and isinstance(node.value, ast.Name)
        and node.value.id == 'self'
    )


def _find_self_pk_violations(source: str) -> list[tuple[int, str]]:
    """Return (lineno, snippet) for each problematic `self.pk` usage.

    Flags:
    - `if self.pk:` / `if not self.pk:` / `if self.pk is None` etc.
      (`self.pk` in a boolean Test of an If)
    - `foo = self.pk is None` / `... is not None`
      (`self.pk` in a Compare with Is / IsNot against None)
    - `while self.pk:`

    Does NOT flag:
    - `self.pk` as a RHS value (`obj.filter(pk=self.pk)`) — legitimate
    - `self.pk = something` — legitimate (assignment)
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    violations: list[tuple[int, str]] = []
    source_lines = source.splitlines()

    for node in ast.walk(tree):
        # `if self.pk:` / `if not self.pk:` / `while self.pk:`
        if isinstance(node, (ast.If, ast.While)):
            test = node.test
            # Strip leading `not`
            if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
                test = test.operand
            if _is_self_pk_attribute(test):
                violations.append((
                    node.lineno,
                    source_lines[node.lineno - 1].strip() if node.lineno <= len(source_lines) else '',
                ))

        # `self.pk is None` / `self.pk is not None` anywhere
        if isinstance(node, ast.Compare):
            if _is_self_pk_attribute(node.left) and any(
                isinstance(op, (ast.Is, ast.IsNot)) and isinstance(c, ast.Constant) and c.value is None
                for op, c in zip(node.ops, node.comparators)
            ):
                violations.append((
                    node.lineno,
                    source_lines[node.lineno - 1].strip() if node.lineno <= len(source_lines) else '',
                ))

    return violations


@register()
def check_secure_model_save_self_pk(app_configs, **kwargs):
    """W001: flag `self.pk`-based new-row detection in SecureModel.save()."""
    from django.apps import apps as django_apps
    from Tracker.models.core import SecureModel

    warnings: list = []

    for model in django_apps.get_models():
        if not issubclass(model, SecureModel) or model is SecureModel:
            continue
        # Only check save() defined on THIS class, not inherited
        if 'save' not in model.__dict__:
            continue

        try:
            source = inspect.getsource(model.save)
        except (OSError, TypeError):
            # Compiled source or C extension — skip
            continue

        violations = _find_self_pk_violations(source)
        for lineno, snippet in violations:
            warnings.append(Warning(
                f"{model.__module__}.{model.__name__}.save() uses `self.pk` "
                f"to detect a new row, but SecureModel assigns uuid7 PKs at "
                f"instantiation time — `self.pk` is ALWAYS populated. This "
                f"check is silently wrong (either always True or always "
                f"False depending on variant).",
                hint=(
                    "Use `self._state.adding` instead:\n"
                    "    if self._state.adding:  # True only on insert\n"
                    "    if not self._state.adding:  # True on update\n"
                    f"Offending line (approx): {snippet!r}"
                ),
                obj=model,
                id='Tracker.W001',
            ))

    return warnings
