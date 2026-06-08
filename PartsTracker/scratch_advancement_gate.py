"""
Throwaway sandbox for the step-advancement gate + lot-cohesion engine.

Run me: `PYTHONIOENCODING=utf-8 python scratch_advancement_gate.py`

Everything is dataclasses + functions. No Django, no DB. The point is to
make the lot-cohesion advancement model concrete before touching real
models. Delete when done.

Mental model:
- The engine's unit of advancement is the LOT (the parts at a given
  WorkOrder × Step where `split_from_cohort=False`).
- `advance_lot_step` is the only sanctioned public entry. It checks
  every part's gate; advances all atomically when all clear.
- Advancement is event-driven, not button-driven. State-changing events
  fire `try_advance_lot`. The function is idempotent.
- Splits are the only manual lever. Permission/reason gated.
- Rework = a kind of split that routes the part to a `rework_target_step`
  defined by the process flow, not to the next step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


# Enum names match Tracker.models.dwi.SubstepScope and friends.
class SubstepScope(str, Enum):
    SAMPLED = "sampled"   # was SAMPLED
    BATCH = "batch"       # was BATCH


class SamplingOutcome(str, Enum):
    SELECTED = "selected"
    DESELECTED = "deselected"
    PENDING = "pending"


class SplitReason(str, Enum):
    QUARANTINE = "quarantine"
    REWORK = "rework"
    EXPEDITE = "expedite"
    CUSTOMER_PULL = "customer_pull"
    SCRAP = "scrap"


# Matches Tracker.models.mes_lite.WorkOrderStatus exactly. The engine
# only advances IN_PROGRESS WOs.
class WorkOrderStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    WAITING_FOR_OPERATOR = "waiting_for_operator"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Matches Tracker.models.mes_lite.StepExecution.status enum. Gate only
# evaluates IN_PROGRESS executions; terminal states (SKIPPED, CANCELLED,
# ROLLED_BACK) are end-states.
class StepExecutionStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


# Matches Tracker.models.dwi.SequencingMode.
class SequencingMode(str, Enum):
    SEQUENTIAL = "sequential"   # substep N requires N-1 satisfied first
    FREE_ORDER = "free_order"


# Matches Tracker.models.mes_lite.StepEdge — the real routing graph.
# Sandbox previously used Step.next_step + Step.rework_target_step.
# Real code routes via edges; we mirror that here.
class StepEdgeType(str, Enum):
    DEFAULT = "default"         # canonical forward path
    REWORK = "rework"           # rework split routes through this edge


# ---------------------------------------------------------------------------
# Domain objects (mocks of the eventual Django models)
# ---------------------------------------------------------------------------


@dataclass
class SamplingRule:
    name: str
    selector: Callable[["Part", "Step"], SamplingOutcome]


@dataclass
class Substep:
    id: int
    title: str
    scope: SubstepScope = SubstepScope.SAMPLED
    sampling_rule: SamplingRule | None = None
    is_optional: bool = False
    is_critical: bool = False
    allow_not_applicable: bool = False
    # NOTE: in-flight parts are protected from mid-run substep edits via
    # the existing UQMES Process versioning (Processes.create_new_version
    # snapshots the entire substep config when a WO starts). No
    # substep-level `version` field needed.


@dataclass
class StepEdge:
    """A routing edge between two Steps. Matches the real
    Tracker.models.mes_lite.StepEdge model — forward flow, rework
    diversions, alternates, and escalations all live as edges in a
    graph, not as direct FKs on the Step."""
    from_step: "Step"
    to_step: "Step"
    edge_type: StepEdgeType = StepEdgeType.DEFAULT


class Step:
    """Routing graph node. Forward flow + rework + alternates all live as
    StepEdges on `edges_out`. The `next_step` and `rework_target_step`
    properties below are convenience shims that translate to/from edges
    so existing tests still read cleanly."""

    def __init__(
        self,
        id: int,
        name: str,
        substeps: list[Substep] | None = None,
        sequencing_mode: SequencingMode = SequencingMode.FREE_ORDER,
        next_step: "Step | None" = None,
        rework_target_step: "Step | None" = None,
        edges_out: list[StepEdge] | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.substeps = substeps if substeps is not None else []
        self.sequencing_mode = sequencing_mode
        self.edges_out: list[StepEdge] = edges_out if edges_out is not None else []
        if next_step is not None:
            self.next_step = next_step  # uses the property setter
        if rework_target_step is not None:
            self.rework_target_step = rework_target_step

    def add_edge(self, to_step: "Step", edge_type: StepEdgeType = StepEdgeType.DEFAULT) -> StepEdge:
        e = StepEdge(from_step=self, to_step=to_step, edge_type=edge_type)
        self.edges_out.append(e)
        return e

    # ----- Backward-compat sugar for the test cases -----

    @property
    def next_step(self) -> "Step | None":
        for e in self.edges_out:
            if e.edge_type == StepEdgeType.DEFAULT:
                return e.to_step
        return None

    @next_step.setter
    def next_step(self, to_step: "Step | None") -> None:
        self.edges_out = [e for e in self.edges_out if e.edge_type != StepEdgeType.DEFAULT]
        if to_step is not None:
            self.add_edge(to_step, StepEdgeType.DEFAULT)

    @property
    def rework_target_step(self) -> "Step | None":
        for e in self.edges_out:
            if e.edge_type == StepEdgeType.REWORK:
                return e.to_step
        return None

    @rework_target_step.setter
    def rework_target_step(self, to_step: "Step | None") -> None:
        self.edges_out = [e for e in self.edges_out if e.edge_type != StepEdgeType.REWORK]
        if to_step is not None:
            self.add_edge(to_step, StepEdgeType.REWORK)

    def __repr__(self) -> str:
        return f"Step(id={self.id}, name={self.name!r})"


@dataclass
class Part:
    id: int
    serial: str
    work_order: "WorkOrder"
    current_step: Step
    # When True, this part advances independently of its WO+step cohort.
    # Quarantine, rework, expedite, scrap all set this. Splits are
    # one-way in v1 — no re-merging.
    split_from_cohort: bool = False
    split_reason: SplitReason | None = None
    split_at: datetime | None = None


@dataclass
class WorkOrder:
    id: int
    parts: list[Part] = field(default_factory=list)
    status: WorkOrderStatus = WorkOrderStatus.IN_PROGRESS


@dataclass
class StepExecution:
    id: int
    part: Part
    step: Step
    # Naming matches the real StepExecution.visit_number field; rework
    # loops produce a new execution row with an incremented number so
    # prior-visit completions don't satisfy the current gate.
    visit_number: int = 1
    status: StepExecutionStatus = StepExecutionStatus.IN_PROGRESS


@dataclass
class SamplingDecision:
    """Append-only. Outcome of evaluating a substep's sampling_rule for
    a specific (step_execution, substep). On rule supersession (AQL
    escalation, fallback ruleset triggering) the new row sets
    `superseded_by` on the old one. `ruleset_version` answers "what
    rule was active when this was decided"; the decision is always
    made by code, so there's no `decided_by` field."""
    step_execution_id: int
    substep_id: int
    outcome: SamplingOutcome
    ruleset_version: int = 1
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    superseded_by_id: int | None = None
    id: int = 0


@dataclass
class BatchExecution:
    id: int
    work_order: WorkOrder
    step: Step
    parts: list[Part]
    sealed_at: datetime | None = None


@dataclass
class SubstepCompletion:
    """If we adopt this in real models, it should inherit
    Tracker.models.qms.VoidableModel — that gives us is_voided +
    voided_at + voided_by + void_reason for free, matching the
    existing void semantics on QualityReports etc."""
    substep_id: int
    step_execution_id: int | None = None
    batch_execution_id: int | None = None
    marked_not_applicable: bool = False
    na_reason_code: str = ""
    # VoidableModel-style fields. `void()` sets is_voided=True + voided_at
    # + void_reason; the gate ignores voided rows.
    is_voided: bool = False
    voided_at: datetime | None = None
    void_reason: str = ""


# ---------------------------------------------------------------------------
# In-memory "tables" + event log so we can see what fired
# ---------------------------------------------------------------------------


@dataclass
class Event:
    name: str
    payload: dict


@dataclass
class World:
    sampling_decisions: list[SamplingDecision] = field(default_factory=list)
    completions: list[SubstepCompletion] = field(default_factory=list)
    batches: list[BatchExecution] = field(default_factory=list)
    executions: dict[tuple[int, int, int], StepExecution] = field(default_factory=dict)
    next_exec_id: int = 1000
    event_log: list[Event] = field(default_factory=list)
    wos: list[WorkOrder] = field(default_factory=list)

    def register(self, wo: WorkOrder) -> None:
        if wo not in self.wos:
            self.wos.append(wo)

    # ----- accessors -----

    def get_or_create_execution(self, part: Part, step: Step) -> StepExecution:
        # Find the latest visit for this (part, step).
        existing = [
            se for (pid, sid, _v), se in self.executions.items()
            if pid == part.id and sid == step.id
        ]
        if existing:
            return max(existing, key=lambda se: se.visit_number)
        visit = 1
        self.next_exec_id += 1
        se = StepExecution(id=self.next_exec_id, part=part, step=step, visit_number=visit)
        self.executions[(part.id, step.id, visit)] = se
        return se

    def bump_visit(self, part: Part, step: Step) -> StepExecution:
        existing = [
            se for (pid, sid, _v), se in self.executions.items()
            if pid == part.id and sid == step.id
        ]
        next_visit = max((se.visit_number for se in existing), default=0) + 1
        self.next_exec_id += 1
        se = StepExecution(id=self.next_exec_id, part=part, step=step, visit_number=next_visit)
        self.executions[(part.id, step.id, next_visit)] = se
        return se

    def decision_for(self, step_execution: StepExecution, substep: Substep) -> SamplingDecision | None:
        live = [
            d for d in self.sampling_decisions
            if d.step_execution_id == step_execution.id
            and d.substep_id == substep.id
            and d.superseded_by_id is None
        ]
        return live[0] if live else None

    def per_part_completion(self, step_execution: StepExecution, substep: Substep) -> SubstepCompletion | None:
        # Only live (non-voided) completions for THIS visit count.
        # Prior-visit completions were on a different StepExecution id,
        # so they're naturally excluded.
        for c in self.completions:
            if (
                c.step_execution_id == step_execution.id
                and c.substep_id == substep.id
                and not c.is_voided
            ):
                return c
        return None

    def sealed_batch_for(self, part: Part, step: Step) -> BatchExecution | None:
        for b in self.batches:
            if b.step.id == step.id and part in b.parts and b.sealed_at:
                return b
        return None

    def cohort_completion(self, batch: BatchExecution, substep: Substep) -> SubstepCompletion | None:
        for c in self.completions:
            if (
                c.batch_execution_id == batch.id
                and c.substep_id == substep.id
                and not c.is_voided
            ):
                return c
        return None

    def emit(self, name: str, **payload) -> None:
        self.event_log.append(Event(name=name, payload=payload))


# ---------------------------------------------------------------------------
# Sampling-decision evaluation (on part entry to step)
# ---------------------------------------------------------------------------


def evaluate_sampling_on_entry(world: World, step_execution: StepExecution) -> None:
    """Persist one SamplingDecision per substep. Idempotent."""
    for substep in step_execution.step.substeps:
        if world.decision_for(step_execution, substep):
            continue
        if substep.scope == SubstepScope.BATCH:
            outcome = SamplingOutcome.SELECTED
        elif substep.sampling_rule is None:
            outcome = SamplingOutcome.SELECTED
        else:
            outcome = substep.sampling_rule.selector(step_execution.part, step_execution.step)
        world.sampling_decisions.append(SamplingDecision(
            step_execution_id=step_execution.id,
            substep_id=substep.id,
            outcome=outcome,
            id=len(world.sampling_decisions) + 1,
        ))


def supersede_decision(world: World, old: SamplingDecision, new_outcome: SamplingOutcome) -> SamplingDecision:
    """Mark `old` as superseded and create a fresh decision row. Returns
    the new row. Real impl ties this to a new ruleset_version."""
    new = SamplingDecision(
        step_execution_id=old.step_execution_id,
        substep_id=old.substep_id,
        outcome=new_outcome,
        ruleset_version=old.ruleset_version + 1,
        id=len(world.sampling_decisions) + 1,
    )
    old.superseded_by_id = new.id
    world.sampling_decisions.append(new)
    return new


# ---------------------------------------------------------------------------
# Batch seal validation
# ---------------------------------------------------------------------------


def seal_batch(world: World, batch: BatchExecution) -> list[str]:
    """Validates every required BATCH substep has a completion in this
    batch. Returns problems; if empty, applies the seal and fires the
    seal event (which retries lot advancement).

    Invariant: every part in a BatchExecution belongs to the same
    WorkOrder as `batch.work_order`. Multi-WO physical runs (one oven
    cycle serving 3 WOs) are modeled as 3 separate BatchExecution rows,
    each scoped to its own WO. Shared physical-run identity isn't a
    first-class concept — if QA ever needs to reconstruct "which parts
    were in the same physical cycle," they query BatchExecutions by
    `(sealed_at, equipment_id)`. No audit consumer asks for more than
    that, so we don't model it.

    The payoff: cohort ownership is crisp, and the seal handler is
    trivially per-WO — no fan-out logic, no blast-radius bugs.
    """
    problems: list[str] = []
    if not batch.parts:
        problems.append("Batch has no parts")
    foreign = [p for p in batch.parts if p.work_order.id != batch.work_order.id]
    if foreign:
        problems.append(
            f"Batch contains parts from other WOs: {[p.id for p in foreign]}. "
            "One BatchExecution per WO is invariant."
        )
    required = [
        s for s in batch.step.substeps
        if s.scope == SubstepScope.BATCH and not s.is_optional
    ]
    for s in required:
        if not world.cohort_completion(batch, s):
            problems.append(f"Batch substep '{s.title}' has no completion")
    if problems:
        return problems
    batch.sealed_at = datetime.now(timezone.utc)
    world.emit("batch.sealed", batch_id=batch.id)
    try_advance_lot(world, batch.work_order.id, batch.step.id)
    return []


# ---------------------------------------------------------------------------
# Substep completion validation (write-time + gate-time re-check)
# ---------------------------------------------------------------------------


def validate_completion(substep: Substep, completion: SubstepCompletion) -> list[str]:
    problems: list[str] = []
    if completion.marked_not_applicable:
        if substep.is_critical:
            problems.append(f"Substep '{substep.title}' is critical; cannot be marked N/A")
        elif not substep.allow_not_applicable:
            problems.append(f"Substep '{substep.title}' does not allow N/A")
        elif not completion.na_reason_code:
            problems.append(f"N/A on '{substep.title}' requires a reason code")
    return problems


def record_completion(world: World, substep: Substep, completion: SubstepCompletion) -> list[str]:
    """Public completion-write entry. Validates, persists, fires the
    'substep.completed' event which retries lot advancement."""
    problems = validate_completion(substep, completion)
    if problems:
        return problems
    world.completions.append(completion)
    world.emit("substep.completed", substep_id=substep.id)
    # Find the affected (WO, step) and try advancement.
    if completion.step_execution_id is not None:
        se = next(s for s in world.executions.values() if s.id == completion.step_execution_id)
        try_advance_lot(world, se.part.work_order.id, se.step.id)
    return []


# ---------------------------------------------------------------------------
# THE GATE — per-part substep-completion blockers
# ---------------------------------------------------------------------------


def substep_completion_blockers(world: World, step_execution: StepExecution) -> list[str]:
    """The new blocker #8. Re-checks N/A validity at gate time (write-time
    enforcement is best-effort)."""
    blockers: list[str] = []
    part = step_execution.part
    step = step_execution.step

    # Don't evaluate terminal executions. SKIPPED/CANCELLED/ROLLED_BACK
    # are end-states; COMPLETED means we already moved on.
    if step_execution.status not in (
        StepExecutionStatus.PENDING,
        StepExecutionStatus.CLAIMED,
        StepExecutionStatus.IN_PROGRESS,
    ):
        return blockers

    # NOTE: Step.sequencing_mode (SEQUENTIAL / FREE_ORDER) is a UI-side
    # concern — the substep player prevents tapping substep 2 before
    # substep 1. The gate doesn't re-check ordering; if a completion row
    # exists, it counts regardless of when it was recorded.

    for substep in step.substeps:
        if substep.is_optional:
            completion = (
                world.per_part_completion(step_execution, substep)
                if substep.scope == SubstepScope.SAMPLED
                else None
            )
            if completion is None:
                continue

        if substep.scope == SubstepScope.SAMPLED:
            decision = world.decision_for(step_execution, substep)
            if decision is None:
                raise RuntimeError(
                    f"Missing sampling decision for execution {step_execution.id}, "
                    f"substep {substep.id} — entry hook didn't fire."
                )

            if decision.outcome == SamplingOutcome.DESELECTED:
                pass  # rule excluded this part; satisfied
            elif decision.outcome == SamplingOutcome.PENDING:
                # PENDING is NON-BLOCKING. The part is admitted as tentative;
                # re-evaluation on cohort close may flag a retroactive miss
                # (non-blocking nonconformance / recall task), but the gate
                # itself doesn't hold the part.
                pass
            else:  # SELECTED
                completion = world.per_part_completion(step_execution, substep)
                if completion is None:
                    blockers.append(f"Substep '{substep.title}' not completed for this part")
                else:
                    na_problems = validate_completion(substep, completion)
                    if na_problems:
                        blockers.append(
                            f"Substep '{substep.title}' N/A no longer valid: "
                            + "; ".join(na_problems)
                        )

        else:  # BATCH
            batch = world.sealed_batch_for(part, step)
            if batch is None:
                blockers.append(
                    f"Batch substep '{substep.title}' requires a sealed batch covering this part"
                )
            elif not world.cohort_completion(batch, substep):
                blockers.append(
                    f"Batch substep '{substep.title}' has no completion on sealed batch #{batch.id}"
                )

    return blockers


# ---------------------------------------------------------------------------
# LOT ADVANCEMENT — the public engine surface
# ---------------------------------------------------------------------------


def _cohort_parts(world: World, work_order: WorkOrder, step: Step) -> list[Part]:
    return [
        p for p in work_order.parts
        if p.current_step.id == step.id and not p.split_from_cohort
    ]


def try_advance_lot(world: World, work_order_id: int, step_id: int) -> dict:
    """Reactive trigger. Idempotent. Called from every state-changing
    event. Handles BOTH:
      - the cohort (non-split parts at this WO+step) — all-or-none
      - split parts at this same WO+step — each evaluated alone
    """
    work_order = _find_workorder(world, work_order_id)
    if work_order.status != WorkOrderStatus.IN_PROGRESS:
        return {"status": "halted", "reason": f"WO is {work_order.status.value}"}
    try:
        step = _find_step(world, work_order, step_id)
    except LookupError:
        return {"status": "noop", "reason": "step no longer reachable from any part"}

    results: dict = {"cohort": None, "split": []}

    # ----- Cohort path (all-or-none) -----
    cohort = _cohort_parts(world, work_order, step)
    if cohort:
        per_part_results: dict[int, list[str]] = {}
        for part in cohort:
            se = world.get_or_create_execution(part, step)
            evaluate_sampling_on_entry(world, se)
            per_part_results[part.id] = substep_completion_blockers(world, se)

        if any(blockers for blockers in per_part_results.values()):
            results["cohort"] = {"status": "blocked", "blockers_by_part": per_part_results}
        else:
            next_step = step.next_step
            for part in cohort:
                part.current_step = next_step if next_step else step
            world.emit(
                "lot.advanced",
                work_order_id=work_order.id,
                from_step_id=step.id,
                to_step_id=next_step.id if next_step else None,
                parts=[p.id for p in cohort],
            )
            results["cohort"] = {"status": "advanced", "parts": [p.id for p in cohort]}
            if next_step:
                try_advance_lot(world, work_order.id, next_step.id)

    # ----- Split path (each part its own cohort-of-one) -----
    split_parts = [
        p for p in work_order.parts
        if p.current_step.id == step.id and p.split_from_cohort
    ]
    for part in split_parts:
        se = world.get_or_create_execution(part, step)
        evaluate_sampling_on_entry(world, se)
        blockers = substep_completion_blockers(world, se)
        if blockers:
            results["split"].append({"part_id": part.id, "status": "blocked", "blockers": blockers})
            continue
        next_step = step.next_step
        prior_step_id = part.current_step.id
        part.current_step = next_step if next_step else step
        world.emit(
            "split_part.advanced",
            part_id=part.id,
            from_step_id=prior_step_id,
            to_step_id=next_step.id if next_step else None,
        )
        results["split"].append({"part_id": part.id, "status": "advanced"})
        if next_step:
            try_advance_lot(world, work_order.id, next_step.id)

    if results["cohort"] is None and not results["split"]:
        return {"status": "noop", "reason": "no parts at this WO+step"}
    return results


# ---------------------------------------------------------------------------
# SPLIT — the only manual lever
# ---------------------------------------------------------------------------


def split_part_from_lot(
    world: World,
    part: Part,
    reason: SplitReason,
    requester: str,
    rework_target: Step | None = None,
) -> dict:
    """Pull a part off its cohort. After this point the part advances
    independently. Permission-gated (placeholder: requester just gets
    audited). Reason required. One-way: no re-merging in v1.

    Rework is just a flavored split: the part is moved to the step's
    `rework_target_step` (or the explicit `rework_target` argument if
    the process flow needs to override). Subsequent advancement runs
    through the rework path; if the rework path leads back to a step
    on the canonical flow, the part travels there alone (does not
    rejoin the original cohort).
    """
    if part.split_from_cohort:
        return {"status": "noop", "reason": "already split"}
    part.split_from_cohort = True
    part.split_reason = reason
    part.split_at = datetime.now(timezone.utc)
    world.emit(
        "part.split",
        part_id=part.id,
        reason=reason.value,
        requester=requester,
    )

    if reason == SplitReason.REWORK:
        # Resolve target: explicit arg wins, else the step's configured
        # rework_target_step. If neither, it's a scrap path waiting on a
        # disposition.
        target = rework_target or part.current_step.rework_target_step
        if target is None:
            return {"status": "split", "next_action": "awaiting disposition (no rework target)"}
        # Move the part. The rework execution is a NEW StepExecution
        # (attempt counter resets at the new step), so prior completions
        # on the rework target don't satisfy it.
        prior_step = part.current_step
        part.current_step = target
        world.bump_visit(part, target)
        world.emit(
            "part.rerouted_for_rework",
            part_id=part.id,
            from_step_id=prior_step.id,
            to_step_id=target.id,
        )

    # Cohort shrunk — the remaining lot may now be ready.
    try_advance_lot(world, part.work_order.id, part.current_step.id)
    return {"status": "split", "reason": reason.value}


# ---------------------------------------------------------------------------
# Helpers for the demo: process flow lookup
# ---------------------------------------------------------------------------


def _find_workorder(world: World, work_order_id: int) -> WorkOrder:
    for wo in world.wos:
        if wo.id == work_order_id:
            return wo
    # Fallback to executions / batches if someone forgot to register.
    for se in world.executions.values():
        if se.part.work_order.id == work_order_id:
            return se.part.work_order
    for b in world.batches:
        if b.work_order.id == work_order_id:
            return b.work_order
        for p in b.parts:
            if p.work_order.id == work_order_id:
                return p.work_order
    raise LookupError(f"WO {work_order_id} not found")


def _find_step(world: World, work_order: WorkOrder, step_id: int) -> Step:
    # Flood-fill across the process graph along every edge_out from each
    # part's current_step. Rework cycles are real, so track visited.
    seen: set[int] = set()
    stack: list[Step] = [p.current_step for p in work_order.parts if p.current_step]
    while stack:
        s = stack.pop()
        if s.id in seen:
            continue
        seen.add(s.id)
        if s.id == step_id:
            return s
        for e in s.edges_out:
            stack.append(e.to_step)
    raise LookupError(f"Step {step_id} not found for WO {work_order.id}")


# ---------------------------------------------------------------------------
# Pretty-printers
# ---------------------------------------------------------------------------


def banner(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def show_lot(world: World, wo: WorkOrder) -> None:
    by_step: dict[str, list[str]] = {}
    for p in wo.parts:
        tag = f"P{p.id}"
        if p.split_from_cohort:
            tag += f"({p.split_reason.value if p.split_reason else 'split'})"
        by_step.setdefault(p.current_step.name, []).append(tag)
    for step_name, tags in by_step.items():
        print(f"  step '{step_name}': {tags}")


def show_events(world: World, since: int = 0) -> int:
    for e in world.event_log[since:]:
        print(f"  [event] {e.name} {e.payload}")
    return len(world.event_log)


# ---------------------------------------------------------------------------
# CASES — now driven by lot-level advancement + event triggers
# ---------------------------------------------------------------------------


def case_1_lot_advances_when_all_parts_complete() -> None:
    banner("Case 1 — 3 parts in a lot, 100% sample, lot advances when all 3 complete")
    world = World()
    next_step = Step(id=11, name="Next op")
    step = Step(
        id=10, name="CNC turn",
        substeps=[Substep(id=101, title="Verify chuck torque")],
        next_step=next_step,
    )
    wo = WorkOrder(id=1)
    parts = [Part(id=i, serial=f"P-{i:03d}", work_order=wo, current_step=step) for i in (1, 2, 3)]
    wo.parts = parts
    world.register(wo)

    show_lot(world, wo)

    log_at = 0
    for p in parts[:2]:
        se = world.get_or_create_execution(p, step)
        evaluate_sampling_on_entry(world, se)
        record_completion(world, step.substeps[0], SubstepCompletion(
            step_execution_id=se.id, substep_id=101,
        ))

    print("After 2 of 3 parts complete (event-driven advancement attempted):")
    log_at = show_events(world, log_at)
    show_lot(world, wo)

    se3 = world.get_or_create_execution(parts[2], step)
    evaluate_sampling_on_entry(world, se3)
    record_completion(world, step.substeps[0], SubstepCompletion(
        step_execution_id=se3.id, substep_id=101,
    ))
    print("After 3rd part completes:")
    log_at = show_events(world, log_at)
    show_lot(world, wo)


def case_2_quarantine_split_lets_lot_proceed() -> None:
    banner("Case 2 — Part quarantined; cohort can't advance until it's split off")
    world = World()
    next_step = Step(id=21, name="Next op")
    step = Step(
        id=20, name="CNC turn",
        substeps=[Substep(id=201, title="Verify chuck torque")],
        next_step=next_step,
    )
    wo = WorkOrder(id=2)
    parts = [Part(id=10 + i, serial=f"Q-{i:03d}", work_order=wo, current_step=step) for i in (1, 2, 3)]
    wo.parts = parts
    world.register(wo)

    log_at = 0
    # Parts 11 and 12 complete; part 13 is quarantined and will be split.
    for p in parts[:2]:
        se = world.get_or_create_execution(p, step)
        evaluate_sampling_on_entry(world, se)
        record_completion(world, step.substeps[0], SubstepCompletion(
            step_execution_id=se.id, substep_id=201,
        ))
    print("After parts 11/12 complete (part 13 still blocked):")
    log_at = show_events(world, log_at)
    show_lot(world, wo)

    print("Splitting part 13 off (quarantine):")
    split_part_from_lot(world, parts[2], SplitReason.QUARANTINE, requester="alex")
    log_at = show_events(world, log_at)
    show_lot(world, wo)


def case_3_batch_seal_drives_advancement() -> None:
    banner("Case 3 — Heat-treat: per-cohort cycle log + first-piece hardness; seal triggers advancement")
    first_piece = SamplingRule(
        name="first_piece_only",
        selector=lambda part, step: (
            SamplingOutcome.SELECTED if part.id == 31 else SamplingOutcome.DESELECTED
        ),
    )
    next_step = Step(id=41, name="Next op")
    step = Step(
        id=40, name="Heat treat",
        substeps=[
            Substep(id=401, title="Log oven cycle parameters", scope=SubstepScope.BATCH),
            Substep(id=402, title="Post-treat hardness check", sampling_rule=first_piece),
        ],
        next_step=next_step,
    )
    world = World()
    wo = WorkOrder(id=3)
    parts = [Part(id=30 + i, serial=f"H-{i:03d}", work_order=wo, current_step=step) for i in (1, 2, 3)]
    wo.parts = parts
    world.register(wo)

    log_at = 0
    # First-piece hardness check for part 31.
    se = world.get_or_create_execution(parts[0], step)
    evaluate_sampling_on_entry(world, se)
    record_completion(world, step.substeps[1], SubstepCompletion(
        step_execution_id=se.id, substep_id=402,
    ))
    print("After first-piece hardness logged (batch still unsealed):")
    log_at = show_events(world, log_at)
    show_lot(world, wo)

    batch = BatchExecution(id=1, work_order=wo, step=step, parts=parts)
    world.batches.append(batch)
    world.completions.append(SubstepCompletion(batch_execution_id=batch.id, substep_id=401))
    seal_problems = seal_batch(world, batch)
    print(f"Sealing batch (problems={seal_problems or 'OK'}):")
    log_at = show_events(world, log_at)
    show_lot(world, wo)


def case_4_rework_splits_to_configured_target() -> None:
    banner("Case 4 — Inspection fails; part splits to rework_target_step in the process")
    world = World()
    # Process flow:
    #   step50 (CNC) -> step60 (Inspection) -> step70 (Pack)
    #   step60.rework_target_step = step55 (Polish for rework)
    step_pack = Step(id=70, name="Pack")
    step_polish = Step(id=55, name="Polish (rework)")
    step_inspect = Step(
        id=60, name="Inspection",
        substeps=[Substep(id=601, title="Final visual")],
        next_step=step_pack,
        rework_target_step=step_polish,
    )
    step_cnc = Step(
        id=50, name="CNC turn",
        substeps=[Substep(id=501, title="Verify chuck torque")],
        next_step=step_inspect,
    )
    # Polish loops back to inspection on completion.
    step_polish.next_step = step_inspect
    step_polish.substeps = [Substep(id=551, title="Buff blemish")]

    wo = WorkOrder(id=4)
    parts = [Part(id=40 + i, serial=f"R-{i:03d}", work_order=wo, current_step=step_inspect) for i in (1, 2)]
    wo.parts = parts
    world.register(wo)

    log_at = 0
    # Both parts get their visual at inspection; part 41 fails operator
    # decision (modeled here as a rework split rather than a passing
    # completion).
    se42 = world.get_or_create_execution(parts[1], step_inspect)
    evaluate_sampling_on_entry(world, se42)
    record_completion(world, step_inspect.substeps[0], SubstepCompletion(
        step_execution_id=se42.id, substep_id=601,
    ))
    print("Part 42 passed inspection (waiting on cohort partner):")
    log_at = show_events(world, log_at)
    show_lot(world, wo)

    print("Splitting part 41 to rework (process flow routes to Polish):")
    split_part_from_lot(world, parts[0], SplitReason.REWORK, requester="alex")
    log_at = show_events(world, log_at)
    show_lot(world, wo)

    # Part 42's cohort shrunk — it should have advanced when 41 left.
    # Now show what happens when polished + re-inspection completes
    # on part 41 (independent of the cohort that already moved on).
    print("Completing polish on split part 41 (engine auto-advances solo to Inspection):")
    se_polish = world.get_or_create_execution(parts[0], step_polish)
    evaluate_sampling_on_entry(world, se_polish)
    record_completion(world, step_polish.substeps[0], SubstepCompletion(
        step_execution_id=se_polish.id, substep_id=551,
    ))
    log_at = show_events(world, log_at)
    show_lot(world, wo)

    print("Completing re-inspection on split part 41 (advances solo to Pack):")
    se_reinspect = world.get_or_create_execution(parts[0], step_inspect)
    evaluate_sampling_on_entry(world, se_reinspect)
    record_completion(world, step_inspect.substeps[0], SubstepCompletion(
        step_execution_id=se_reinspect.id, substep_id=601,
    ))
    log_at = show_events(world, log_at)
    show_lot(world, wo)


def case_5_cascading_advancement_through_ready_steps() -> None:
    banner("Case 5 — Cascade: lot advances through multiple steps when downstream steps are already satisfied")
    world = World()
    # Three steps; the middle one has no substeps so any part landing
    # there satisfies the gate immediately.
    step3 = Step(id=83, name="Ship")
    step2 = Step(id=82, name="Auto-pass (no substeps)", next_step=step3)
    step1 = Step(
        id=81, name="CNC turn",
        substeps=[Substep(id=811, title="Verify chuck torque")],
        next_step=step2,
    )
    wo = WorkOrder(id=5)
    parts = [Part(id=80 + i, serial=f"C-{i:03d}", work_order=wo, current_step=step1) for i in (1, 2)]
    wo.parts = parts
    world.register(wo)

    log_at = 0
    for p in parts:
        se = world.get_or_create_execution(p, step1)
        evaluate_sampling_on_entry(world, se)
        record_completion(world, step1.substeps[0], SubstepCompletion(
            step_execution_id=se.id, substep_id=811,
        ))
    print("After both parts complete the chuck torque check:")
    log_at = show_events(world, log_at)
    show_lot(world, wo)


# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# EXTENDED CASES — every base behavior the engine needs to handle
# ---------------------------------------------------------------------------


def case_6_pending_sampling_is_non_blocking() -> None:
    banner("Case 6 — PENDING sampling decision is non-blocking (admit tentative)")
    # Rule says "I don't know yet — cohort-close will tell us." The gate
    # must NOT hold the part. A real impl would also queue a cohort-close
    # re-evaluation task; the sandbox just shows the gate doesn't block.
    rule = SamplingRule(
        name="awaiting_cohort_close",
        selector=lambda part, step: SamplingOutcome.PENDING,
    )
    world = World()
    next_step = Step(id=601, name="Next op")
    step = Step(
        id=600, name="Op with deferred sample",
        substeps=[Substep(id=6001, title="Deferred OD check", sampling_rule=rule)],
        next_step=next_step,
    )
    wo = WorkOrder(id=6)
    part = Part(id=60, serial="X-001", work_order=wo, current_step=step)
    wo.parts = [part]
    world.register(wo)
    se = world.get_or_create_execution(part, step)
    evaluate_sampling_on_entry(world, se)
    # No completion exists; PENDING is non-blocking; lot should advance.
    try_advance_lot(world, wo.id, step.id)
    show_lot(world, wo)
    show_events(world, 0)


def case_7_empty_batch_seal_rejected() -> None:
    banner("Case 7 — Sealing a batch with no parts or missing completions is rejected")
    world = World()
    step = Step(
        id=700, name="Heat treat",
        substeps=[Substep(id=7001, title="Cycle log", scope=SubstepScope.BATCH)],
    )
    wo = WorkOrder(id=7)
    parts = [Part(id=70 + i, serial=f"E-{i}", work_order=wo, current_step=step) for i in (1, 2)]
    wo.parts = parts
    world.register(wo)

    # Empty batch.
    b_empty = BatchExecution(id=70, work_order=wo, step=step, parts=[])
    world.batches.append(b_empty)
    print("Empty batch seal:", seal_batch(world, b_empty))

    # Non-empty batch but missing completion.
    b_full = BatchExecution(id=71, work_order=wo, step=step, parts=parts)
    world.batches.append(b_full)
    print("Non-empty batch with no cycle-log completion:", seal_batch(world, b_full))

    # Now record the completion and seal — should succeed.
    world.completions.append(SubstepCompletion(batch_execution_id=b_full.id, substep_id=7001))
    print("After completion + reseal:", seal_batch(world, b_full) or "OK")


def case_8_multiple_batches_per_step() -> None:
    banner("Case 8 — Three oven cycles, each its own BatchExecution; each part belongs to exactly one")
    world = World()
    next_step = Step(id=801, name="Next op")
    step = Step(
        id=800, name="Heat treat",
        substeps=[Substep(id=8001, title="Cycle log", scope=SubstepScope.BATCH)],
        next_step=next_step,
    )
    wo = WorkOrder(id=8)
    parts = [Part(id=80 + i, serial=f"M-{i:02d}", work_order=wo, current_step=step) for i in range(1, 7)]
    wo.parts = parts
    world.register(wo)

    # 3 separate physical oven runs, 2 parts each.
    cycles = []
    for cycle_idx in range(3):
        members = parts[cycle_idx * 2: cycle_idx * 2 + 2]
        b = BatchExecution(id=80 + cycle_idx, work_order=wo, step=step, parts=members)
        world.batches.append(b)
        world.completions.append(SubstepCompletion(batch_execution_id=b.id, substep_id=8001))
        seal_batch(world, b)
        cycles.append(b)
        print(f"Cycle {cycle_idx + 1} sealed, parts {[p.id for p in members]}")

    show_lot(world, wo)


def case_9_multi_wo_physical_run_uses_one_batch_per_wo() -> None:
    banner("Case 9 — One physical oven cycle serves 3 WOs; each WO gets its own BatchExecution")
    # Design rule: BatchExecution is per-WO. Even when the physical
    # operation is shared (same oven, same temperature, same dwell),
    # the audit and advancement model is per-WO. The operator captures
    # the cycle data once on a tablet and the system writes 3
    # BatchExecution rows. Shared physical-run identity isn't modeled
    # — if SPC or recall needs it, they query by (sealed_at,
    # equipment_id), no extra concept required.
    #
    # Outcome: NO fan-out logic, NO blast-radius bug. Each batch seal
    # advances exactly its own WO's cohort.
    world = World()
    next_step = Step(id=901, name="Next op")
    step = Step(
        id=900, name="Heat treat",
        substeps=[Substep(id=9001, title="Cycle log", scope=SubstepScope.BATCH)],
        next_step=next_step,
    )
    wos = [WorkOrder(id=100 + i) for i in (1, 2, 3)]
    for wo in wos:
        wo.parts = [
            Part(id=wo.id * 10 + j, serial=f"W{wo.id}-{j}",
                 work_order=wo, current_step=step)
            for j in (1, 2)
        ]
        world.register(wo)

    # Three BatchExecutions, one per WO. Operator-side UI replicates
    # the captured cycle data across all three; semantically each row
    # is independently sealable.
    batches = []
    for wo in wos:
        b = BatchExecution(id=90 + wo.id, work_order=wo, step=step, parts=list(wo.parts))
        world.batches.append(b)
        world.completions.append(SubstepCompletion(batch_execution_id=b.id, substep_id=9001))
        batches.append(b)

    # Demonstrate the foreign-part guard: try to put a WO 101 part into
    # the WO 102 batch. Should be rejected at seal time.
    print("Sanity: cross-WO membership in a single batch is rejected:")
    bad = BatchExecution(id=999, work_order=wos[0], step=step, parts=wos[0].parts + [wos[1].parts[0]])
    world.batches.append(bad)
    print("  seal_problems:", seal_batch(world, bad))

    # Now seal each real per-WO batch. Each one advances exactly its
    # own cohort.
    for b in batches:
        problems = seal_batch(world, b)
        print(f"WO {b.work_order.id} seal: {problems or 'OK'}")

    for wo in wos:
        print(f"WO {wo.id}:")
        show_lot(world, wo)


def case_10_na_validation_failures() -> None:
    banner("Case 10 — N/A write-time validation: 3 reject paths + 1 valid path")
    world = World()
    step = Step(id=1000, name="Misc")
    wo = WorkOrder(id=10)
    part = Part(id=1000, serial="N-1", work_order=wo, current_step=step)
    wo.parts = [part]
    world.register(wo)
    se = world.get_or_create_execution(part, step)

    cases = [
        ("Required substep marked N/A",
         Substep(id=1, title="Mandatory check"),
         dict(marked_not_applicable=True, na_reason_code="oops")),
        ("Critical substep marked N/A",
         Substep(id=2, title="Safety torque", is_critical=True, is_optional=True, allow_not_applicable=True),
         dict(marked_not_applicable=True, na_reason_code="anything")),
        ("Optional substep allowing N/A but no reason code",
         Substep(id=3, title="Visual", is_optional=True, allow_not_applicable=True),
         dict(marked_not_applicable=True, na_reason_code="")),
        ("Optional substep allowing N/A WITH reason — should accept",
         Substep(id=4, title="Optional photo", is_optional=True, allow_not_applicable=True),
         dict(marked_not_applicable=True, na_reason_code="not_applicable_for_part_geometry")),
    ]

    for label, substep, na_kwargs in cases:
        comp = SubstepCompletion(step_execution_id=se.id, substep_id=substep.id, **na_kwargs)
        problems = record_completion(world, substep, comp)
        print(f"  {label}: {problems or 'ACCEPTED'}")


def case_11_gate_rechecks_na_validity_post_write() -> None:
    banner("Case 11 — Engineer flips is_critical=True AFTER N/A row was written; gate re-checks and blocks")
    world = World()
    next_step = Step(id=1101, name="Next op")
    substep = Substep(id=11001, title="Torque", is_optional=True, allow_not_applicable=True)
    step = Step(id=1100, name="Assembly", substeps=[substep], next_step=next_step)
    wo = WorkOrder(id=11)
    part = Part(id=1100, serial="C-1", work_order=wo, current_step=step)
    wo.parts = [part]
    world.register(wo)
    se = world.get_or_create_execution(part, step)
    evaluate_sampling_on_entry(world, se)

    # Write a valid N/A row.
    na = SubstepCompletion(
        step_execution_id=se.id, substep_id=substep.id,
        marked_not_applicable=True, na_reason_code="not_torqued_in_this_assembly",
    )
    print("Write-time validation:", record_completion(world, substep, na) or "ACCEPTED")
    print("Gate before flip:", substep_completion_blockers(world, se) or "PASS")

    # Engineer retroactively marks the substep critical (model change /
    # admin edit / migration import).
    substep.is_critical = True
    print("After flipping is_critical=True:")
    print("Gate after flip:", substep_completion_blockers(world, se) or "PASS")


def case_12_optional_substep_skipped_when_no_completion() -> None:
    banner("Case 12 — Optional substep with no completion is skipped; doesn't block lot")
    world = World()
    next_step = Step(id=1201, name="Next op")
    step = Step(
        id=1200, name="Assembly",
        substeps=[
            Substep(id=12001, title="Mandatory check"),
            Substep(id=12002, title="Optional photo", is_optional=True),
        ],
        next_step=next_step,
    )
    wo = WorkOrder(id=12)
    part = Part(id=1200, serial="O-1", work_order=wo, current_step=step)
    wo.parts = [part]
    world.register(wo)
    se = world.get_or_create_execution(part, step)
    evaluate_sampling_on_entry(world, se)

    record_completion(world, step.substeps[0], SubstepCompletion(
        step_execution_id=se.id, substep_id=12001,
    ))
    # Optional photo never captured — should still advance.
    show_lot(world, wo)
    show_events(world, 0)


def case_13_scrap_split_no_rework_target_part_held() -> None:
    banner("Case 13 — Scrap split with no rework target; part awaits disposition, cohort advances")
    world = World()
    next_step = Step(id=1301, name="Next op")
    step = Step(
        id=1300, name="Inspection",
        substeps=[Substep(id=13001, title="Final visual")],
        next_step=next_step,
    )
    wo = WorkOrder(id=13)
    parts = [Part(id=1300 + i, serial=f"S-{i}", work_order=wo, current_step=step) for i in (1, 2)]
    wo.parts = parts
    world.register(wo)

    # Part 1301 passes.
    se1 = world.get_or_create_execution(parts[1], step)
    evaluate_sampling_on_entry(world, se1)
    record_completion(world, step.substeps[0], SubstepCompletion(
        step_execution_id=se1.id, substep_id=13001,
    ))
    # Part 1300 split to scrap (no rework target on Inspection).
    result = split_part_from_lot(world, parts[0], SplitReason.SCRAP, requester="alex")
    print("Scrap split result:", result)
    show_lot(world, wo)


def case_14_rework_loop_bumps_attempt() -> None:
    banner("Case 14 — Rework loop: attempt 2 doesn't inherit attempt 1's completion")
    world = World()
    step_pack = Step(id=1401, name="Pack")
    step_polish = Step(id=1402, name="Polish")
    step_inspect = Step(
        id=1400, name="Inspection",
        substeps=[Substep(id=14001, title="Visual")],
        next_step=step_pack,
        rework_target_step=step_polish,
    )
    step_polish.next_step = step_inspect
    step_polish.substeps = [Substep(id=14002, title="Buff")]

    wo = WorkOrder(id=14)
    part = Part(id=1400, serial="L-1", work_order=wo, current_step=step_inspect)
    wo.parts = [part]
    world.register(wo)

    # Attempt 1: operator looks at part, decides it needs rework BEFORE
    # signing off the visual. Split for rework routes to Polish.
    print("Operator decides part needs rework before passing Visual; splitting:")
    split_part_from_lot(world, part, SplitReason.REWORK, requester="alex")
    show_lot(world, wo)
    print(f"  current_step={part.current_step.name}, split_reason={part.split_reason}")

    # Complete the polish work; engine auto-advances solo back to Inspection.
    se_polish = world.get_or_create_execution(part, step_polish)
    evaluate_sampling_on_entry(world, se_polish)
    record_completion(world, step_polish.substeps[0], SubstepCompletion(
        step_execution_id=se_polish.id, substep_id=14002,
    ))
    show_lot(world, wo)

    # Now back at Inspection on a NEW StepExecution (attempt 2).
    se2 = world.get_or_create_execution(part, step_inspect)
    se_attempts_at_inspection = [
        s for (pid, sid, _a), s in world.executions.items()
        if pid == part.id and sid == step_inspect.id
    ]
    print(f"Inspection executions seen so far: {[s.visit_number for s in se_attempts_at_inspection]}")
    print("Gate on new Inspection exec — must block until a fresh Visual is recorded:")
    print(" blockers:", substep_completion_blockers(world, se2) or "PASS")


def case_15_step_with_no_substeps_is_immediate_pass() -> None:
    banner("Case 15 — Step with zero substeps: gate trivially passes; cohort advances on next event")
    world = World()
    next_step = Step(id=1501, name="Done")
    step = Step(id=1500, name="Pass-through")  # no substeps
    step.next_step = next_step
    wo = WorkOrder(id=15)
    parts = [Part(id=1500 + i, serial=f"T-{i}", work_order=wo, current_step=step) for i in (1, 2, 3)]
    wo.parts = parts
    world.register(wo)

    # No events fire on their own; we need something to call
    # try_advance_lot. In real impl that'd be the WO-start hook or the
    # arrival event. Simulate the arrival:
    try_advance_lot(world, wo.id, step.id)
    show_lot(world, wo)
    show_events(world, 0)


def case_16_idempotent_split_and_advance() -> None:
    banner("Case 16 — Calling split twice or try_advance_lot repeatedly is idempotent")
    world = World()
    next_step = Step(id=1601, name="Next op")
    step = Step(id=1600, name="Op", substeps=[Substep(id=16001, title="Check")], next_step=next_step)
    wo = WorkOrder(id=16)
    part = Part(id=1600, serial="I-1", work_order=wo, current_step=step)
    wo.parts = [part]
    world.register(wo)

    r1 = split_part_from_lot(world, part, SplitReason.QUARANTINE, requester="alex")
    r2 = split_part_from_lot(world, part, SplitReason.QUARANTINE, requester="alex")
    print("First split:", r1)
    print("Second split (noop expected):", r2)

    # Repeated advancement attempts are also safe.
    for _ in range(3):
        try_advance_lot(world, wo.id, step.id)
    show_events(world, 0)
    show_lot(world, wo)


def case_17_mixed_per_part_and_per_cohort_in_same_step() -> None:
    banner("Case 17 — Same step has 1 SAMPLED (100%) + 1 BATCH substep")
    world = World()
    next_step = Step(id=1701, name="Next op")
    step = Step(
        id=1700, name="Heat treat + per-part scan",
        substeps=[
            Substep(id=17001, title="Scan part in"),  # SAMPLED
            Substep(id=17002, title="Cycle log", scope=SubstepScope.BATCH),
        ],
        next_step=next_step,
    )
    wo = WorkOrder(id=17)
    parts = [Part(id=1700 + i, serial=f"X-{i}", work_order=wo, current_step=step) for i in (1, 2)]
    wo.parts = parts
    world.register(wo)

    # Operators scan each part in (per-part substep). Lot still blocked
    # on the unsealed batch.
    for p in parts:
        se = world.get_or_create_execution(p, step)
        evaluate_sampling_on_entry(world, se)
        record_completion(world, step.substeps[0], SubstepCompletion(
            step_execution_id=se.id, substep_id=17001,
        ))
    print("After per-part scans complete (still blocked on BATCH):")
    show_lot(world, wo)

    # Seal the batch with the cycle-log completion.
    b = BatchExecution(id=170, work_order=wo, step=step, parts=parts)
    world.batches.append(b)
    world.completions.append(SubstepCompletion(batch_execution_id=b.id, substep_id=17002))
    seal_batch(world, b)
    print("After batch seal:")
    show_lot(world, wo)


def case_18_override_approval_retries_advancement() -> None:
    banner("Case 18 — Operator-level blocker cleared by a (mocked) approved override fires try_advance_lot")
    # The sandbox doesn't model StepOverride, but the integration shape
    # is: the override approval write-path calls try_advance_lot. Here
    # we just demonstrate the call.
    world = World()
    next_step = Step(id=1801, name="Next op")
    step = Step(id=1800, name="Op", substeps=[Substep(id=18001, title="Check")], next_step=next_step)
    wo = WorkOrder(id=18)
    part = Part(id=1800, serial="O-1", work_order=wo, current_step=step)
    wo.parts = [part]
    world.register(wo)

    # Gate currently blocks — no completion.
    se = world.get_or_create_execution(part, step)
    evaluate_sampling_on_entry(world, se)
    print("Pre-override blockers:", substep_completion_blockers(world, se))

    # Operator records the completion under override (real impl: the
    # override row's existence might let the gate pass even with no
    # completion). Here we simulate the easier path: override approval
    # triggers a no-op retry that the operator then satisfies by
    # completing the substep. The point of the case is just to show
    # that override.approved fires try_advance_lot.
    record_completion(world, step.substeps[0], SubstepCompletion(
        step_execution_id=se.id, substep_id=18001,
    ))
    # Simulate the override.approved event firing try_advance_lot again
    # (idempotent — second call is a noop since the lot already moved).
    world.emit("override.approved", part_id=part.id)
    try_advance_lot(world, wo.id, step.id)
    show_events(world, 0)
    show_lot(world, wo)


def case_19_split_part_inherits_cohort_completion_from_pre_split_batch() -> None:
    banner("Case 19 — Part is in a sealed batch; later splits; gate honors the inherited cohort completion")
    world = World()
    next_step = Step(id=1901, name="Next op")
    step = Step(
        id=1900, name="Heat treat",
        substeps=[Substep(id=19001, title="Cycle log", scope=SubstepScope.BATCH)],
        next_step=next_step,
    )
    wo = WorkOrder(id=19)
    parts = [Part(id=1900 + i, serial=f"H-{i}", work_order=wo, current_step=step) for i in (1, 2)]
    wo.parts = parts
    world.register(wo)

    # Both parts go in a batch, batch seals.
    b = BatchExecution(id=190, work_order=wo, step=step, parts=parts)
    world.batches.append(b)
    world.completions.append(SubstepCompletion(batch_execution_id=b.id, substep_id=19001))
    seal_batch(world, b)

    # NOW split part 1900 (cohort already advanced — show that split
    # doesn't break the historical relationship to the sealed batch).
    print("After seal, both parts moved to Next op:")
    show_lot(world, wo)

    # Roll back the parts to the heat-treat step to illustrate the
    # inheritance check (since lot already advanced, walk back manually).
    parts[0].current_step = step
    split_part_from_lot(world, parts[0], SplitReason.QUARANTINE, requester="alex")
    # If gate is asked about this split part at the heat-treat step, it
    # must STILL see the sealed batch as covering it.
    se = world.get_or_create_execution(parts[0], step)
    print("Split-part gate at heat-treat (should pass because the seal still covers it):")
    print(" blockers:", substep_completion_blockers(world, se) or "PASS")


def case_20_concurrent_advancement_idempotent() -> None:
    banner("Case 20 — Two completion events fire 'simultaneously'; only one advancement occurs")
    world = World()
    next_step = Step(id=2001, name="Next op")
    step = Step(
        id=2000, name="Op",
        substeps=[Substep(id=20001, title="Check")],
        next_step=next_step,
    )
    wo = WorkOrder(id=20)
    parts = [Part(id=2000 + i, serial=f"R-{i}", work_order=wo, current_step=step) for i in (1, 2)]
    wo.parts = parts
    world.register(wo)

    log_at = 0
    se1 = world.get_or_create_execution(parts[0], step)
    se2 = world.get_or_create_execution(parts[1], step)
    evaluate_sampling_on_entry(world, se1)
    evaluate_sampling_on_entry(world, se2)
    world.completions.append(SubstepCompletion(step_execution_id=se1.id, substep_id=20001))
    world.completions.append(SubstepCompletion(step_execution_id=se2.id, substep_id=20001))

    # Two events fire from the two completions. In real impl these are
    # two Celery tasks. Here we just call back-to-back; the second one
    # should be a noop because the cohort already advanced.
    try_advance_lot(world, wo.id, step.id)
    try_advance_lot(world, wo.id, step.id)
    log_at = show_events(world, log_at)
    show_lot(world, wo)
    print("(Both calls succeeded; second was a noop. Real impl needs a row-level lock or "
          "advisory lock keyed on (wo, step) to make this safe under real concurrency.)")


def case_21_aql_percentage_sampling() -> None:
    banner("Case 21 — AQL: 30% of cohort selected; only selected parts must complete the substep")
    # Sample roughly the first 30% by part id ordering (deterministic).
    def aql_30(part: Part, step: Step) -> SamplingOutcome:
        cohort_ids = sorted(p.id for p in part.work_order.parts)
        keep = max(1, int(len(cohort_ids) * 0.3))
        return SamplingOutcome.SELECTED if part.id in cohort_ids[:keep] else SamplingOutcome.DESELECTED

    rule = SamplingRule(name="aql_30", selector=aql_30)
    world = World()
    next_step = Step(id=2101, name="Next op")
    step = Step(
        id=2100, name="Inspection (AQL 30%)",
        substeps=[Substep(id=21001, title="Gauge check", sampling_rule=rule)],
        next_step=next_step,
    )
    wo = WorkOrder(id=21)
    parts = [Part(id=2100 + i, serial=f"A-{i:02d}", work_order=wo, current_step=step) for i in range(1, 11)]
    wo.parts = parts
    world.register(wo)

    # Evaluate decisions for everyone.
    for p in parts:
        evaluate_sampling_on_entry(world, world.get_or_create_execution(p, step))
    selected = [d.step_execution_id for d in world.sampling_decisions if d.outcome == SamplingOutcome.SELECTED]
    deselected_count = sum(1 for d in world.sampling_decisions if d.outcome == SamplingOutcome.DESELECTED)
    print(f"Selected execs: {len(selected)}; deselected execs: {deselected_count}")

    # Complete the substep for SELECTED parts only.
    for se in list(world.executions.values()):
        d = world.decision_for(se, step.substeps[0])
        if d and d.outcome == SamplingOutcome.SELECTED:
            record_completion(world, step.substeps[0], SubstepCompletion(
                step_execution_id=se.id, substep_id=21001,
            ))
    show_lot(world, wo)


def case_22_rule_supersession_invalidates_prior_decision() -> None:
    banner("Case 22 — Rule supersession: previously DESELECTED part is now SELECTED; gate flips to blocking")
    rule = SamplingRule(name="initial", selector=lambda p, s: SamplingOutcome.DESELECTED)
    world = World()
    next_step = Step(id=2201, name="Next op")
    substep = Substep(id=22001, title="OD check", sampling_rule=rule)
    step = Step(id=2200, name="Inspection", substeps=[substep], next_step=next_step)
    wo = WorkOrder(id=22)
    part = Part(id=2200, serial="S-1", work_order=wo, current_step=step)
    wo.parts = [part]
    world.register(wo)

    se = world.get_or_create_execution(part, step)
    evaluate_sampling_on_entry(world, se)
    print("Initial decision (DESELECTED — part skips this substep):")
    print(" gate:", substep_completion_blockers(world, se) or "PASS")

    # Engineer publishes a new ruleset version that selects everyone.
    old = world.decision_for(se, substep)
    supersede_decision(world, old, SamplingOutcome.SELECTED)
    print("After supersession to SELECTED (no completion exists yet):")
    print(" gate:", substep_completion_blockers(world, se) or "PASS")
    print(f" decision rows for this exec: "
          f"{[(d.id, d.outcome.value, d.superseded_by_id) for d in world.sampling_decisions]}")


def case_23_rework_target_has_different_substep_set() -> None:
    banner("Case 23 — Rework target step has its OWN substeps; gate uses target's, not original's")
    step_inspect = Step(id=2300, name="Inspection",
                       substeps=[Substep(id=23001, title="Final visual")])
    step_machine = Step(id=2310, name="Re-machine",
                       substeps=[
                           Substep(id=23101, title="Re-cut OD"),
                           Substep(id=23102, title="Deburr"),
                       ])
    step_machine.next_step = step_inspect
    step_inspect.rework_target_step = step_machine

    world = World()
    wo = WorkOrder(id=23)
    part = Part(id=2300, serial="X-1", work_order=wo, current_step=step_inspect)
    wo.parts = [part]
    world.register(wo)

    split_part_from_lot(world, part, SplitReason.REWORK, requester="alex")
    print("After rework split:")
    show_lot(world, wo)

    se = world.get_or_create_execution(part, step_machine)
    evaluate_sampling_on_entry(world, se)
    print("Gate at Re-machine step uses Re-machine's substeps (2 of them):")
    print(" blockers:", substep_completion_blockers(world, se))

    # Complete only one — still blocked on the second.
    record_completion(world, step_machine.substeps[0], SubstepCompletion(
        step_execution_id=se.id, substep_id=23101,
    ))
    print("After 1 of 2 re-machine substeps complete:")
    print(" blockers:", substep_completion_blockers(world, se))
    record_completion(world, step_machine.substeps[1], SubstepCompletion(
        step_execution_id=se.id, substep_id=23102,
    ))
    print("After both complete — should advance to Inspection:")
    show_lot(world, wo)


def case_24_voided_completion_no_longer_satisfies() -> None:
    banner("Case 24 — Voided SubstepCompletion stops satisfying the gate")
    world = World()
    next_step = Step(id=2401, name="Next op")
    substep = Substep(id=24001, title="Torque check")
    step = Step(id=2400, name="Assembly", substeps=[substep], next_step=next_step)
    wo = WorkOrder(id=24)
    part = Part(id=2400, serial="V-1", work_order=wo, current_step=step)
    wo.parts = [part]
    world.register(wo)

    se = world.get_or_create_execution(part, step)
    evaluate_sampling_on_entry(world, se)
    record_completion(world, substep, SubstepCompletion(
        step_execution_id=se.id, substep_id=24001,
    ))
    print("After valid completion (advanced):")
    show_lot(world, wo)

    # Roll back to test the void scenario in isolation.
    part.current_step = step
    completion = world.per_part_completion(se, substep)
    print("Gate before void:", substep_completion_blockers(world, se) or "PASS")
    completion.is_voided = True
    completion.voided_at = datetime.now(timezone.utc)
    completion.void_reason = "QA found the torque wrench was out of calibration"
    print("Gate after void (substep is now unsatisfied):")
    print(" blockers:", substep_completion_blockers(world, se))


def case_26_cancelled_wo_halts_advancement() -> None:
    banner("Case 26 — WorkOrder.status = CANCELLED halts the engine; events become noops")
    world = World()
    next_step = Step(id=2601, name="Next op")
    substep = Substep(id=26001, title="Check")
    step = Step(id=2600, name="Op", substeps=[substep], next_step=next_step)
    wo = WorkOrder(id=26)
    parts = [Part(id=2600 + i, serial=f"C-{i}", work_order=wo, current_step=step) for i in (1, 2)]
    wo.parts = parts
    world.register(wo)

    # Complete substep for both — would normally advance.
    for p in parts:
        se = world.get_or_create_execution(p, step)
        evaluate_sampling_on_entry(world, se)
        world.completions.append(SubstepCompletion(step_execution_id=se.id, substep_id=26001))

    # Cancel the WO BEFORE the advancement task runs.
    wo.status = WorkOrderStatus.CANCELLED
    result = try_advance_lot(world, wo.id, step.id)
    print(f"try_advance_lot on cancelled WO: {result}")
    show_lot(world, wo)


def case_27_event_replay_out_of_order_safe() -> None:
    banner("Case 27 — batch.sealed event delivered BEFORE the last substep.completed (retry/replay)")
    world = World()
    next_step = Step(id=2701, name="Next op")
    step = Step(
        id=2700, name="Heat treat",
        substeps=[
            Substep(id=27001, title="Cycle log", scope=SubstepScope.BATCH),
            Substep(id=27002, title="Per-part scan"),
        ],
        next_step=next_step,
    )
    wo = WorkOrder(id=27)
    parts = [Part(id=2700 + i, serial=f"R-{i}", work_order=wo, current_step=step) for i in (1, 2)]
    wo.parts = parts
    world.register(wo)

    # Seal the batch BEFORE per-part scans are recorded. The seal event
    # fires try_advance_lot, which finds the cohort still missing the
    # per-part substep and stays put — noop.
    b = BatchExecution(id=270, work_order=wo, step=step, parts=parts)
    world.batches.append(b)
    world.completions.append(SubstepCompletion(batch_execution_id=b.id, substep_id=27001))
    seal_batch(world, b)
    print("After seal arrives early (per-part scans still missing):")
    show_lot(world, wo)

    # Now the per-part scans arrive. Each completion fires try_advance_lot;
    # the second one succeeds and advances the cohort.
    for p in parts:
        se = world.get_or_create_execution(p, step)
        evaluate_sampling_on_entry(world, se)
        record_completion(world, step.substeps[1], SubstepCompletion(
            step_execution_id=se.id, substep_id=27002,
        ))
    print("After per-part scans arrive (replay-safe — engine just re-tries):")
    show_lot(world, wo)


def case_30_terminal_step_execution_skips_gate() -> None:
    banner("Case 30 — StepExecution.status terminal: gate returns no blockers (already past this step)")
    world = World()
    step = Step(id=3000, name="Done op", substeps=[Substep(id=30001, title="Check")])
    wo = WorkOrder(id=30)
    part = Part(id=3000, serial="T-1", work_order=wo, current_step=step)
    wo.parts = [part]
    world.register(wo)
    se = world.get_or_create_execution(part, step)
    evaluate_sampling_on_entry(world, se)

    print("In-progress exec, no completion — should block:")
    print(" blockers:", substep_completion_blockers(world, se))

    # Mark exec COMPLETED (or SKIPPED / CANCELLED / ROLLED_BACK).
    se.status = StepExecutionStatus.COMPLETED
    print(f"After se.status = {se.status.value} — gate skips terminal execs:")
    print(" blockers:", substep_completion_blockers(world, se) or "PASS")


def case_28_tenant_scope_structural_note() -> None:
    banner("Case 28 — Cross-tenant safety is a structural property, not a runtime check")
    print("Sandbox doesn't model tenants. Real impl: SecureManager auto-scopes every")
    print("query in the gate (SubstepCompletion.objects, SamplingDecision.objects,")
    print("BatchExecution.objects). The gate must use `.objects` inside a")
    print("`tenant_context()` request, never `.unscoped` or `.all_tenants`.")
    print()
    print("Tests should:")
    print("  1. Set tenant_context to tenant A.")
    print("  2. Create a (WO, step, completion) in tenant A.")
    print("  3. Switch to tenant B.")
    print("  4. Call try_advance_lot(WO_a.id, step.id). Expect LookupError / 404 —")
    print("     NOT silent leakage of tenant A's data.")


def main() -> None:
    case_1_lot_advances_when_all_parts_complete()
    case_2_quarantine_split_lets_lot_proceed()
    case_3_batch_seal_drives_advancement()
    case_4_rework_splits_to_configured_target()
    case_5_cascading_advancement_through_ready_steps()


def extended() -> None:
    case_6_pending_sampling_is_non_blocking()
    case_7_empty_batch_seal_rejected()
    case_8_multiple_batches_per_step()
    case_9_multi_wo_physical_run_uses_one_batch_per_wo()
    case_10_na_validation_failures()
    case_11_gate_rechecks_na_validity_post_write()
    case_12_optional_substep_skipped_when_no_completion()
    case_13_scrap_split_no_rework_target_part_held()
    case_14_rework_loop_bumps_attempt()
    case_15_step_with_no_substeps_is_immediate_pass()
    case_16_idempotent_split_and_advance()
    case_17_mixed_per_part_and_per_cohort_in_same_step()
    case_18_override_approval_retries_advancement()
    case_19_split_part_inherits_cohort_completion_from_pre_split_batch()
    case_20_concurrent_advancement_idempotent()
    case_21_aql_percentage_sampling()
    case_22_rule_supersession_invalidates_prior_decision()
    case_23_rework_target_has_different_substep_set()
    case_24_voided_completion_no_longer_satisfies()
    case_26_cancelled_wo_halts_advancement()
    case_27_event_replay_out_of_order_safe()
    case_30_terminal_step_execution_skips_gate()
    case_28_tenant_scope_structural_note()


if __name__ == "__main__":
    main()
    extended()
