"""
Process diff service — structured JSON diff between two Process versions.

Used by `ProcessChangeRequest` submission to capture a tangible diff of
what the engineer changed on the DRAFT vs the approved baseline. The
diff is stored on `ProcessChangeRequest.proposed_change_diff` and
becomes the approver's reference (alongside the engineer's narrative in
`proposed_change`).

Shape:

    {
        "from_process_id": "<uuid>",
        "to_process_id": "<uuid>",
        "from_version": 3,
        "to_version": 4,
        "process": {
            # Top-level field diffs on the Process row itself
            "name": {"from": "Foo", "to": "Bar"},
            ...
        },
        "steps": {
            "added": [{"id": "...", "name": "...", "step_type": "..."}],
            "removed": [{"id": "...", "name": "..."}],
            "modified": [
                {"id": "...", "name": "...",
                 "changes": {"is_terminal": {"from": false, "to": true}}},
            ],
        },
        "edges": {
            # Matched by the identity of each end, so a step edited in the draft
            # (a new version, same identity) leaves its connections unchanged.
            "added":   [{"from_step": "...", "to_step": "...",
                         "from_step_identity": "...", "to_step_identity": "...",
                         "edge_type": "..."}],
            "removed": [...],
        },
    }

Notes:
- Steps, substeps and both ends of every edge are matched by `identity_id`, which
  stays the same across versions: editing a step in a PCR draft forks a new Step
  row, and only a real change should show.
- Substeps are grouped under their parent step's identity (`substeps` block).
- Computing the diff is read-only. `rebase.py` re-applies a PCR's diff onto a fresh
  draft when the approved process moved underneath it.
"""
from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from Tracker.models import Processes


# Process-level scalar fields we diff. Skip identity / lifecycle fields.
_PROCESS_DIFF_FIELDS = (
    "name",
    "is_remanufactured",
    "category",
)

# Step-level scalar fields we diff (per ProcessStep + Step). Covers the
# user-visible properties an engineer is likely to change via the
# process flow editor or the step form.
_STEP_DIFF_FIELDS = (
    "name",
    "description",
    "expected_duration",
    "pass_threshold",
    "step_type",
    "is_decision_point",
    "is_terminal",
    "max_visits",
    "is_critical",
    "requires_first_piece_inspection",
    "requires_qa_signoff",
    "sampling_required",
    "min_sampling_rate",
    "block_on_quarantine",
    "block_on_measurement_failure",
    "sequencing_mode",
    # A Repair node's code: which repair a check can send a unit to.
    "repair_code_id",
)

# An edge's identity: the logical step at each end (Step.identity_id), its type, and
# `pre_approved` — so making a repair pre-approved at a check, or taking that away,
# shows as a changed branch rather than as no change at all. Ends are matched by step
# IDENTITY, not row id: editing a step in a PCR draft forks a new version and
# re-points the draft's edges to it, and keyed by row id every connection of an
# edited step read as removed and re-added though the routing hadn't changed.


def compute_process_diff(from_process: "Processes", to_process: "Processes") -> Dict[str, Any]:
    """Compare two Process versions and return a structured diff dict.

    `from_process` is the baseline (typically the APPROVED process the
    PCR targets); `to_process` is the DRAFT being proposed. The diff
    shape is documented in this module's header.

    Read-only — does not mutate either process. Safe to call repeatedly.
    """
    diff: Dict[str, Any] = {
        "from_process_id": str(from_process.id),
        "to_process_id": str(to_process.id),
        "from_version": getattr(from_process, "version", None),
        "to_version": getattr(to_process, "version", None),
        "process": _diff_scalars(from_process, to_process, _PROCESS_DIFF_FIELDS),
        "steps": _diff_steps(from_process, to_process),
        "edges": _diff_edges(from_process, to_process),
        "substeps": _diff_substeps(from_process, to_process),
    }
    return diff


def diff_has_changes(diff: Dict[str, Any] | None) -> bool:
    """Whether a diff from `compute_process_diff` changes anything at all."""
    if not diff:
        return False
    steps = diff.get("steps") or {}
    edges = diff.get("edges") or {}
    return bool(
        diff.get("process")
        or steps.get("added") or steps.get("removed") or steps.get("modified")
        or edges.get("added") or edges.get("removed")
        or diff.get("substeps")
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _diff_scalars(a, b, fields: tuple[str, ...]) -> Dict[str, Dict[str, Any]]:
    """Return {field: {from, to}} for any field that differs between a and b."""
    result: Dict[str, Dict[str, Any]] = {}
    for f in fields:
        va = getattr(a, f, None)
        vb = getattr(b, f, None)
        if va != vb:
            result[f] = {"from": _jsonable(va), "to": _jsonable(vb)}
    return result


def _diff_steps(from_process: "Processes", to_process: "Processes") -> Dict[str, Any]:
    """Step-membership + per-step scalar diff. Steps are matched by id.

    Steps are matched across processes by `identity_id` — a stable UUID
    copied unchanged across versions. Two Step rows that share an
    identity_id are versions of the same logical step, even if their
    row ids differ (which happens when one side has been versioned via
    the PCR-DRAFT editing flow). Field changes between them surface as
    a "modified" entry.

    Steps that appear on only one identity_id after reconciliation are
    genuinely added or removed.
    """
    from_steps = [ps.step for ps in from_process.process_steps.all()]
    to_steps = [ps.step for ps in to_process.process_steps.all()]
    from_by_identity = {step.identity_id: step for step in from_steps}
    to_by_identity = {step.identity_id: step for step in to_steps}

    added: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    modified: List[Dict[str, Any]] = []

    for identity, b in to_by_identity.items():
        a = from_by_identity.get(identity)
        if a is None:
            added.append(_step_summary(b))
            continue
        changes = _diff_scalars(a, b, _STEP_DIFF_FIELDS)
        if changes:
            modified.append({**_step_summary(b), "changes": changes})

    for identity, a in from_by_identity.items():
        if identity not in to_by_identity:
            removed.append(_step_summary(a))

    return {"added": added, "removed": removed, "modified": modified}


_SUBSTEP_DIFF_FIELDS = (
    "title",
    "order",
    "is_optional",
    "is_critical",
    "is_inspection_point",
    "requires_signature",
    "allow_not_applicable",
    "scope",
    "expected_duration",
)


def _diff_substeps(from_process: "Processes", to_process: "Processes") -> Dict[str, Any]:
    """Per-Step substep diff, keyed by parent Step's identity_id.

    Each Step on the process has its own Substep rows (forked when the
    Step is versioned). Match substeps by their stable `identity_id`,
    grouped under their parent Step's identity_id so the consumer can
    show "substeps changed on the Cleaning step."

    body_blocks comparisons are intentionally shallow — a deep TipTap
    JSON diff would be expensive and noisy; we just flag that the
    block changed so the UI can offer a side-by-side body view.
    """
    from Tracker.models.dwi import Substep

    result: Dict[str, Any] = {}

    from_steps_by_identity = {
        ps.step.identity_id: ps.step for ps in from_process.process_steps.all()
    }
    to_steps_by_identity = {
        ps.step.identity_id: ps.step for ps in to_process.process_steps.all()
    }
    shared_step_identities = (
        set(from_steps_by_identity) & set(to_steps_by_identity)
    )
    if not shared_step_identities:
        return result

    for step_identity in shared_step_identities:
        from_step = from_steps_by_identity[step_identity]
        to_step = to_steps_by_identity[step_identity]
        from_subs = {
            s.identity_id: s for s in Substep.objects.filter(archived=False, step=from_step)
        }
        to_subs = {
            s.identity_id: s for s in Substep.objects.filter(archived=False, step=to_step)
        }
        added: List[Dict[str, Any]] = []
        removed: List[Dict[str, Any]] = []
        modified: List[Dict[str, Any]] = []

        for identity, b in to_subs.items():
            a = from_subs.get(identity)
            if a is None:
                added.append(_substep_summary(b))
                continue
            changes = _diff_scalars(a, b, _SUBSTEP_DIFF_FIELDS)
            if a.body_blocks != b.body_blocks:
                changes["body_blocks"] = {"changed": True}
            if changes:
                modified.append({**_substep_summary(b), "changes": changes})

        for identity, a in from_subs.items():
            if identity not in to_subs:
                removed.append(_substep_summary(a))

        if added or removed or modified:
            result[str(step_identity)] = {
                "added": added,
                "removed": removed,
                "modified": modified,
            }

    return result


def _substep_summary(substep) -> Dict[str, Any]:
    return {
        "id": str(substep.id),
        "identity_id": str(substep.identity_id),
        "title": substep.title,
        "order": substep.order,
    }


def _diff_edges(from_process: "Processes", to_process: "Processes") -> Dict[str, Any]:
    """Edge-membership diff, edges matched by `_edge_key`."""
    from_edges = {_edge_key(e): e for e in
                  from_process.step_edges.select_related('from_step', 'to_step')}
    to_edges = {_edge_key(e): e for e in
                to_process.step_edges.select_related('from_step', 'to_step')}

    added = [_edge_summary(to_edges[k]) for k in to_edges.keys() - from_edges.keys()]
    removed = [_edge_summary(from_edges[k]) for k in from_edges.keys() - to_edges.keys()]
    return {"added": added, "removed": removed}


def _step_summary(step) -> Dict[str, Any]:
    return {
        "id": str(step.id),
        # identity_id is the stable cross-version key — use it when
        # cross-referencing changes between two diffs (e.g. detecting
        # whether two PCRs touched the same logical step at approval).
        "identity_id": str(step.identity_id),
        "name": step.name,
        "step_type": getattr(step, "step_type", None),
    }


def _edge_key(edge) -> tuple:
    return (edge.from_step.identity_id, edge.to_step.identity_id,
            edge.edge_type, edge.pre_approved)


def _edge_summary(edge) -> Dict[str, Any]:
    return {
        "from_step": str(edge.from_step_id),
        "to_step": str(edge.to_step_id),
        # The key the edge was matched on — what rebase resolves the ends by.
        "from_step_identity": str(edge.from_step.identity_id),
        "to_step_identity": str(edge.to_step.identity_id),
        # Names for the reader; the ids above are what rebase resolves.
        "from_step_name": edge.from_step.name,
        "to_step_name": edge.to_step.name,
        "edge_type": edge.edge_type,
        "pre_approved": edge.pre_approved,
    }


def _jsonable(v: Any) -> Any:
    """Coerce values into JSON-serializable form for the diff payload."""
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    return str(v)
