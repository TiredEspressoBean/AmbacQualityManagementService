"""A required reman capture belongs on a reman-only step.

The reman capture nodes — components harvested, components installed, rebuild findings —
describe a core. A new build has no core, so a REQUIRED one on a step a new-build route
also runs can never be satisfied, and the unit sticks there. Substep "Not applicable" was
the escape hatch; it is retired (user decision 2026-10-20), so the authoring has to be
right instead. Refused at both doors: writing such a node onto a shared step's substep,
and adding a step that carries one to a non-reman process.
"""
from __future__ import annotations

REMAN_CAPTURE_TYPES = frozenset({
    "harvestedComponentCapture", "componentInstallCapture", "rebuildFindingCapture",
})


def _required_reman_labels(body) -> list[str]:
    """Labels of the required (or strict-enumeration) reman capture nodes in a body."""
    out: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            attrs = node.get("attrs") or {}
            if node.get("type") in REMAN_CAPTURE_TYPES and (
                    attrs.get("required") is True or attrs.get("strict_enumeration") is True):
                out.append(attrs.get("label") or node["type"])
            for child in node.get("content") or []:
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(body or {})
    return out


def _message(label, process_name) -> str:
    return (f"A required reman capture ('{label}') can't go on a step that new builds also "
            f"run ({process_name}): a new build has no core to record. Put it on a "
            f"reman-only step.")


def substep_refusal(step, body, *, optional=False) -> str | None:
    """Why this substep body can't be saved on `step`, or None. An optional substep is
    skipped by a unit it doesn't apply to, so it can carry one."""
    if optional:
        return None
    labels = _required_reman_labels(body)
    if not labels or step is None:
        return None
    from Tracker.models import Processes
    shared = (Processes.objects  # tenant-safe: .objects auto-scopes; FK-correlated to a scoped step
              .filter(process_steps__step=step, is_remanufactured=False, archived=False)
              .first())
    return _message(labels[0], shared.name) if shared else None


def process_step_refusal(process, step) -> str | None:
    """Why `step` can't be added to `process`, or None."""
    if process is None or step is None or process.is_remanufactured:
        return None
    for sub in step.substeps.filter(archived=False, is_optional=False):  # tenant-safe: reverse FK from a scoped step
        labels = _required_reman_labels(sub.body_blocks)
        if labels:
            return _message(labels[0], process.name)
    return None
