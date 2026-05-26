"""
CEL expression engine for NotificationRule conditions.

Three concerns:

  1. **Compile** — turn a source string into an executable program. Surfaces
     CEL syntax errors as `CelValidationError` with field-level messages.
  2. **Validate against event** — given a `(source, event_code)` pair, check
     that every `payload.X` reference matches a field on the event's payload
     dataclass. Unknown fields produce "did you mean" suggestions.
  3. **Evaluate** — run a compiled program against a payload + optional
     `owner_user` context. Returns bool; runtime errors are caught and
     logged (returning False) so a corrupt payload doesn't crash dispatch.

The module wraps the `cel-python` package (PyPI: `cel-python`, import: `celpy`)
and surfaces a stable API the rest of the notification subsystem can rely on.
The dispatcher and the rule serializer are the only intended callers.

References:
  - CEL spec: https://github.com/google/Also
  cel-spec
  - cel-python: https://github.com/cloud-custodian/cel-python
"""
from __future__ import annotations

import difflib
import logging
import re
from dataclasses import fields, is_dataclass
from typing import Any

import celpy
from celpy import celparser

logger = logging.getLogger(__name__)


# Single shared environment. Variables (`payload`, `owner_user`) are typed
# loosely as MapType — cel-python does runtime evaluation against actual
# dicts; strict type checking against the payload's dataclass shape is done
# separately by `validate_against_event` rather than by the CEL compiler.
_ENV = celpy.Environment()


# =============================================================================
# Public API
# =============================================================================

class CelValidationError(ValueError):
    """Raised when a CEL expression fails save-time validation.

    `errors` is a list of structured dicts that serializers can turn into
    field-level DRF errors. Each entry has at minimum:
      - `field`: the form field to highlight (usually `'conditions_source'`)
      - `message`: human-readable error
      - `suggestion`: optional "did you mean" replacement
    """

    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__("; ".join(e.get("message", "CEL error") for e in errors))


def compile_condition(source: str):
    """Compile a CEL source string into a runnable program.

    Returns `None` for empty/whitespace-only input (which the evaluator
    treats as "always match"). Raises `CelValidationError` on syntax errors.
    """
    if not source or not source.strip():
        return None
    try:
        ast = _ENV.compile(source)
    except celparser.CELParseError as exc:
        raise CelValidationError([{
            "field": "conditions_source",
            "message": f"Syntax error: {exc}",
        }]) from exc
    return _ENV.program(ast)


def validate_against_event(source: str, event_code: str) -> None:
    """Validate a CEL expression against an event's payload schema.

    Two-pass check:
      1. CEL syntax (via `compile_condition`).
      2. Every `payload.X` reference must match a field on the event's
         registered payload dataclass. Unknown fields produce a
         `CelValidationError` with "did you mean" suggestions sourced
         from `difflib.get_close_matches`.

    Empty conditions are always valid. Unknown event codes raise as well —
    `NotificationRule.clean()` checks `event_code` separately, but we
    re-check here so the function is safe to call standalone.
    """
    if not source or not source.strip():
        return

    # Step 1 — syntax check (raises on parse error).
    compile_condition(source)

    # Step 2 — field-existence check against the event's payload schema.
    from Tracker.services.core.notifications.registry import EVENT_REGISTRY

    event = EVENT_REGISTRY.get(event_code)
    if event is None:
        raise CelValidationError([{
            "field": "event_code",
            "message": f"Unknown event code: {event_code!r}",
        }])

    schema = event.payload_schema
    if not is_dataclass(schema):
        return

    known_fields = {f.name for f in fields(schema)}
    referenced = _extract_payload_references(source)

    errors: list[dict] = []
    for ref in sorted(referenced):
        if ref in known_fields:
            continue
        suggestion = _did_you_mean(ref, known_fields)
        msg = f"Field 'payload.{ref}' does not exist on {schema.__name__}."
        if suggestion:
            msg += f" Did you mean 'payload.{suggestion}'?"
        errors.append({
            "field": "conditions_source",
            "reference": f"payload.{ref}",
            "message": msg,
            "suggestion": f"payload.{suggestion}" if suggestion else None,
        })

    if errors:
        raise CelValidationError(errors)


def evaluate(
    program,
    payload: dict[str, Any],
    owner_user: dict[str, Any] | None = None,
) -> bool:
    """Evaluate a compiled program against a payload + optional owner context.

    `program` is the return value of `compile_condition()`. `None` means
    "no conditions, always match" → returns True. Runtime errors are
    caught and logged at WARNING; the function returns False so a corrupt
    payload doesn't fire spurious notifications.

    `owner_user` is the rule's owner (for personal-scope rules that
    reference `owner_user.id` in their conditions). For tenant/customer
    rules, pass `None` or `{}`.
    """
    if program is None:
        return True

    context = {
        "payload": celpy.json_to_cel(payload),
        "owner_user": celpy.json_to_cel(owner_user or {}),
    }
    try:
        result = program.evaluate(context)
        return bool(result)
    except Exception:
        logger.exception(
            "CEL evaluation failed; suppressing rule fire. "
            "payload_keys=%s",
            list(payload.keys())[:10],
        )
        return False


# =============================================================================
# Internals
# =============================================================================

# Matches `payload.<field>` in source. Doesn't try to handle nested paths
# (`payload.customer.id`) because the v1 payload schemas are flat — every
# field is a primitive. If/when nested payloads ship, extend this regex
# AND the AST-walking strategy (regex isn't sufficient for nested grammar).
_PAYLOAD_REF_RE = re.compile(r"\bpayload\.([a-zA-Z_][a-zA-Z0-9_]*)\b")


def _extract_payload_references(source: str) -> set[str]:
    return set(_PAYLOAD_REF_RE.findall(source))


def _did_you_mean(name: str, candidates: set[str]) -> str | None:
    """Closest match from `candidates` to `name`, or None if no near match.

    `cutoff=0.5` is permissive enough to catch transpositions like
    'severty' → 'severity' but tight enough to reject totally-unrelated
    fields.
    """
    matches = difflib.get_close_matches(name, sorted(candidates), n=1, cutoff=0.5)
    return matches[0] if matches else None
