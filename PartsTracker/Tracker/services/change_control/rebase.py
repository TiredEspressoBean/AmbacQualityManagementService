"""
PCR rebase service — detects and resolves baseline drift at approval time.

When two PCRs target the same process and one approves first, the second
PCR's draft is anchored at a baseline that's no longer current. This
module handles the reconciliation:

- `compute_baseline_gap(pcr)` — produces the diff of (PCR's baseline →
  current approved). Empty when nothing has changed under the PCR; non-
  empty when another PCR has approved against the same process line.

- `find_overlapping_fields(intent_diff, gap_diff)` — given the PCR's
  intent and what changed under it, return the set of (identity_id,
  field) tuples present in both. A non-empty set means a real conflict;
  empty means PCR's changes can be lifted onto the new baseline.

- `rebase_pcr_draft(pcr)` — top-level orchestration. Computes intent and
  gap, calls the overlap check, and either:
    * returns a `RebaseConflict` describing the overlap so the caller
      can refuse approval; or
    * applies PCR's non-overlapping intent on top of the current
      approved version and points the PCR at a fresh DRAFT for
      approval, returning a `RebaseSuccess`.

Field-level squash is intentionally NOT performed for v1. If two PCRs
touched the same field, the second PCR is blocked and the engineer
decides — keep theirs, accept the baseline, or cancel. That matches
regulated change-control practice where conflicts on controlled
specifications must be human-resolved, not silently merged.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from django.db import transaction

from Tracker.models import (
    Processes,
    ProcessChangeRequest,
    ProcessStatus,
    ProcessStep,
    StepEdge,
)
from Tracker.services.change_control.diff import compute_process_diff
from Tracker.services.mes.steps import (
    add_step_to_process,
    create_new_step_version,
    remove_step_from_process,
)


@dataclass(frozen=True)
class FieldConflict:
    """A single (identity_id, field, baseline_value, intent_value,
    approved_value) tuple — what PCR-B tried to set, vs. what's already
    been approved by some other PCR. Used both to format the error and
    to drive the resolution UI."""
    step_identity_id: str
    step_name: str
    field: str
    intent_value: Any
    approved_value: Any


@dataclass(frozen=True)
class RebaseConflict:
    """Returned when an open PCR can't be rebased automatically because
    its intent overlaps with intervening approved changes."""
    pcr_id: str
    baseline_version_id: str
    current_approved_id: str
    conflicts: List[FieldConflict]


@dataclass(frozen=True)
class RebaseSuccess:
    """Returned when a rebase produced a fresh DRAFT against current
    approved that carries PCR-B's intent forward. The PCR's
    `draft_process_version` FK has been updated to point at this draft.
    """
    pcr_id: str
    previous_draft_id: str
    new_draft_id: str


def find_current_approved(baseline_process: Processes) -> Processes:
    """Return the latest APPROVED row in `baseline_process`'s version
    line. Handles branched chains — multiple open PCRs sibling-forking
    from the same baseline produce a tree, and the answer is the most
    recently-promoted APPROVED node anywhere in that tree.

    Filters out archived rows and prefers `is_current_version=True`
    candidates so a branched tree where one sibling approved and
    flipped the baseline can't accidentally return a deeper,
    superseded APPROVED node. Falls back to `baseline_process` when
    no descendant is APPROVED (typical state during in-flight PCRs
    that haven't been implemented yet — the baseline itself is still
    the live spec).
    """
    visited: set = set()
    queue: list = [baseline_process]
    chain: list = []
    while queue:
        node = queue.pop(0)
        if node.id in visited:
            continue
        visited.add(node.id)
        chain.append(node)
        # tenant-safe: anchored on previous_version=<in-tenant Process>.
        # Exclude archived rows from the walk so soft-deleted drafts
        # can't be considered as "current approved" candidates.
        for successor in (
            Processes.objects
            .filter(previous_version=node, archived=False)
            .exclude(id__in=visited)
        ):
            queue.append(successor)
        if len(visited) > 100:  # Defensive bound on tree exploration.
            break

    approved = [
        p for p in chain
        if p.status == ProcessStatus.APPROVED and not p.archived
    ]
    if not approved:
        return baseline_process
    # Prefer rows still marked `is_current_version=True`. In a healthy
    # branched tree exactly one APPROVED node carries that flag once
    # `approve_process` has flipped the predecessor; older APPROVED
    # ancestors are no longer current. Fall through to latest-by-
    # version only when no candidate carries the flag (legacy data
    # from before the flip was wired up).
    current = [p for p in approved if getattr(p, 'is_current_version', False)]
    pool = current or approved
    return max(pool, key=lambda p: p.version or 0)


def find_overlapping_fields(
    intent_diff: Dict[str, Any],
    gap_diff: Dict[str, Any],
    current_approved: Processes,
) -> List[FieldConflict]:
    """Return the field-level overlaps between two diffs. Step-level
    add / remove conflicts also surface here as pseudo-fields (`__add__`,
    `__remove__`) so the caller can refuse on those too.
    """
    conflicts: List[FieldConflict] = []

    intent_modified = {
        m['identity_id']: m for m in intent_diff.get('steps', {}).get('modified', [])
    }
    gap_modified = {
        m['identity_id']: m for m in gap_diff.get('steps', {}).get('modified', [])
    }
    shared = set(intent_modified) & set(gap_modified)
    for identity in shared:
        intent_changes = intent_modified[identity].get('changes', {})
        gap_changes = gap_modified[identity].get('changes', {})
        overlap_fields = set(intent_changes) & set(gap_changes)
        for field in overlap_fields:
            conflicts.append(FieldConflict(
                step_identity_id=identity,
                step_name=intent_modified[identity].get('name', ''),
                field=field,
                intent_value=intent_changes[field].get('to') if isinstance(intent_changes[field], dict) else None,
                approved_value=gap_changes[field].get('to') if isinstance(gap_changes[field], dict) else None,
            ))

    # Step-level conflicts: PCR removed a step that was also removed (or
    # modified) by the approved diff. We surface these as field conflicts
    # under a synthetic field name so the resolution UI can list them
    # alongside the regular ones.
    intent_removed = {s['identity_id'] for s in intent_diff.get('steps', {}).get('removed', [])}
    gap_removed = {s['identity_id'] for s in gap_diff.get('steps', {}).get('removed', [])}
    intent_added_ids = {s['identity_id'] for s in intent_diff.get('steps', {}).get('added', [])}
    gap_added_ids = {s['identity_id'] for s in gap_diff.get('steps', {}).get('added', [])}

    # If PCR-B removed a step the approved diff also modified: conflict.
    for identity in intent_removed & set(gap_modified):
        conflicts.append(FieldConflict(
            step_identity_id=identity,
            step_name=gap_modified[identity].get('name', ''),
            field='__removed_by_pcr_modified_by_baseline__',
            intent_value=None,
            approved_value='modified',
        ))
    # If PCR-B modified a step the approved diff removed: conflict.
    for identity in gap_removed & set(intent_modified):
        conflicts.append(FieldConflict(
            step_identity_id=identity,
            step_name=intent_modified[identity].get('name', ''),
            field='__modified_by_pcr_removed_by_baseline__',
            intent_value='modified',
            approved_value=None,
        ))
    # Two PCRs that both add a step with the same identity would only
    # happen via a weird workflow (forking the same DRAFT) — defensive
    # check for completeness.
    for identity in intent_added_ids & gap_added_ids:
        conflicts.append(FieldConflict(
            step_identity_id=identity,
            step_name='',
            field='__added_by_both__',
            intent_value='added',
            approved_value='added',
        ))

    del current_approved  # not used in detection; reserved for future field-level squash
    return conflicts


def rebase_pcr_draft(pcr: ProcessChangeRequest, *, user) -> RebaseSuccess | RebaseConflict:
    """Reconcile a PCR's draft against the current approved baseline.

    Returns a `RebaseSuccess` when the PCR's intent can be lifted onto
    the new baseline (no overlap), or a `RebaseConflict` when human
    decision is required.

    No-op (returns RebaseSuccess with same draft id) when the PCR is
    already anchored at current. Callers should treat that as proceed.
    """
    draft = pcr.draft_process_version
    if draft is None:
        # Legacy text-only PCR with no draft attached. No rebase
        # possible — caller proceeds with normal approval flow which
        # falls back to forking from target_process at PCO creation.
        return RebaseSuccess(
            pcr_id=str(pcr.id),
            previous_draft_id='',
            new_draft_id='',
        )
    baseline = draft.previous_version
    if baseline is None:
        # Draft has no baseline FK — defensive fallback for older PCRs
        # created before the propose flow attached versioning.
        return RebaseSuccess(
            pcr_id=str(pcr.id),
            previous_draft_id=str(draft.id),
            new_draft_id=str(draft.id),
        )

    current_approved = find_current_approved(baseline)
    if current_approved.id == baseline.id:
        # Baseline is still current — no rebase needed.
        return RebaseSuccess(
            pcr_id=str(pcr.id),
            previous_draft_id=str(draft.id),
            new_draft_id=str(draft.id),
        )

    intent_diff = compute_process_diff(baseline, draft)
    gap_diff = compute_process_diff(baseline, current_approved)

    conflicts = find_overlapping_fields(intent_diff, gap_diff, current_approved)
    if conflicts:
        return RebaseConflict(
            pcr_id=str(pcr.id),
            baseline_version_id=str(baseline.id),
            current_approved_id=str(current_approved.id),
            conflicts=conflicts,
        )

    # No overlap — lift PCR's intent onto the current approved baseline.
    # Fork a fresh DRAFT from current_approved and replay PCR's changes.
    with transaction.atomic():
        from Tracker.services.mes.processes import create_new_process_version

        new_draft = create_new_process_version(
            current_approved,
            user=user,
            change_description=(
                f"Rebase of {pcr.artifact_number} from v{baseline.version} "
                f"onto v{current_approved.version}"
            ),
            allow_multiple_drafts=True,
            # Rebase fork is a DRAFT proposal, not a supersession yet.
            supersede_source=False,
        )
        _apply_intent_to_process(new_draft, intent_diff, source_draft=draft, user=user)
        # Repoint the PCR at the rebased DRAFT and archive the old one.
        # Without the archive flip the previous draft sits at cur=True
        # forever even though no PCR points at it, which is what
        # produced the orphan-draft accumulation seen in dev tenants.
        previous_draft_id = str(draft.id)
        draft.archived = True
        draft.is_current_version = False
        draft.save(update_fields=['archived', 'is_current_version', 'updated_at'])
        pcr.draft_process_version = new_draft
        pcr.save(update_fields=['draft_process_version', 'updated_at'])

    return RebaseSuccess(
        pcr_id=str(pcr.id),
        previous_draft_id=previous_draft_id,
        new_draft_id=str(new_draft.id),
    )


def _apply_intent_to_process(
    process: Processes,
    intent_diff: Dict[str, Any],
    *,
    source_draft: Processes,
    user,
) -> None:
    """Replay an intent diff onto a fresh process version. Used by
    rebase to lift PCR's non-conflicting changes onto current approved.

    Walks the diff structure and dispatches to the canonical Step
    services for each operation. Edges are rebuilt from the intent diff
    (additions and removals) on top of whatever the fresh fork copied
    from current_approved.

    `source_draft` is the PCR's previous DRAFT (the source the intent
    was computed against). Step ids in the diff payload are resolved
    via that draft's ProcessStep junction so the lookup is anchored on
    a process we know belongs to the right tenant and chain — never a
    bare `Steps.objects.filter(id=...)` that would accept any row id
    routed through the diff payload.
    """
    steps_block = intent_diff.get('steps', {})
    edges_block = intent_diff.get('edges', {})

    # Apply step-level changes.
    for entry in steps_block.get('removed', []):
        identity = entry['identity_id']
        # tenant-safe: filtered by identity_id (tenant-scoped via FK).
        ps = ProcessStep.objects.filter(
            process=process,
            step__identity_id=identity,
        ).first()
        if ps is not None:
            remove_step_from_process(process, [ps.step_id])

    for entry in steps_block.get('added', []):
        # The intent diff carries the source Step row id. Resolve it
        # via the source draft's ProcessStep junction so we copy both
        # the Step fields AND the original ordering / entry-point flag
        # forward — otherwise the rebased steps land at order=1 and
        # the engineer has to manually re-sequence after every rebase.
        ps_source = ProcessStep.objects.filter(
            process=source_draft,
            step_id=entry['id'],
        ).select_related('step').first()
        if ps_source is None:
            continue
        source = ps_source.step
        add_step_to_process(
            process,
            order=ps_source.order,
            is_entry_point=ps_source.is_entry_point,
            name=source.name,
            step_type=source.step_type,
            description=source.description,
        )

    for entry in steps_block.get('modified', []):
        identity = entry['identity_id']
        # tenant-safe: filtered by identity_id (tenant-scoped via FK).
        ps = ProcessStep.objects.filter(
            process=process,
            step__identity_id=identity,
        ).first()
        if ps is None:
            continue
        # Build field overrides from the diff's `changes` dict — each
        # change is {"from": old, "to": new}; we only want the "to".
        field_overrides = {
            field: change['to']
            for field, change in entry.get('changes', {}).items()
            if isinstance(change, dict) and 'to' in change
        }
        if field_overrides:
            create_new_step_version(
                ps.step,
                user=user,
                change_description=f"Rebase: applied intent on {ps.step.name}",
                process=process,
                **field_overrides,
            )

    # Edge changes — fully rebuild affected edges on the fresh process.
    # `create_new_process_version` copied edges from current_approved
    # already, so we apply additions and removals on top.
    for edge in edges_block.get('removed', []):
        StepEdge.objects.filter(
            process=process,
            from_step__identity_id=_step_identity_for(edge.get('from_step'), source_draft),
            to_step__identity_id=_step_identity_for(edge.get('to_step'), source_draft),
            edge_type=edge.get('edge_type'),
        ).delete()
    for edge in edges_block.get('added', []):
        from_identity = _step_identity_for(edge.get('from_step'), source_draft)
        to_identity = _step_identity_for(edge.get('to_step'), source_draft)
        if not from_identity or not to_identity:
            continue
        # Resolve identity → current Step row on this process.
        from_ps = ProcessStep.objects.filter(
            process=process, step__identity_id=from_identity,
        ).first()
        to_ps = ProcessStep.objects.filter(
            process=process, step__identity_id=to_identity,
        ).first()
        if from_ps and to_ps:
            StepEdge.objects.create(
                process=process,
                from_step=from_ps.step,
                to_step=to_ps.step,
                edge_type=edge.get('edge_type', 'DEFAULT'),
            )


def _step_identity_for(step_id: Optional[str], source_draft: Processes) -> Optional[str]:
    """Resolve a row-id from a diff payload to its identity_id.

    Anchored on the source draft's ProcessStep junction so we never
    look up arbitrary Step rows by id — the diff payload's `step_id`
    must belong to the draft the intent was computed against.
    """
    if not step_id:
        return None
    ps = ProcessStep.objects.filter(
        process=source_draft, step_id=step_id,
    ).select_related('step').first()
    return str(ps.step.identity_id) if ps else None
