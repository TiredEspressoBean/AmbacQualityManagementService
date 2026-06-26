/**
 * OperatorSubstepRuntimePage — Tulip-style player redesign.
 *
 * Architecture (per the design pass we just ran):
 * - One substep at a time, full-bleed, centered max-width on tablet
 * - Top progress rail: Step name + substep dots (filled / current / pending)
 * - Bottom fixed action bar: large "Confirm & next" primary, secondary actions
 * - Substep responses are sealed client-side on confirm (auto-advance);
 *   server flush is opportunistic via `useSubmitSubstep` and forced at
 *   end-of-step
 * - End-of-step review screen — operator sees what they recorded, can jump
 *   back to edit, then "Complete step" flushes the rest
 * - URL carries the current substep index so refresh / kiosk-handoff
 *   resume cleanly
 *
 * Out of scope this iteration (follow-up):
 * - Required-field "amber pill" affordance per capture
 * - Out-of-spec blocked panel for inspection-point measurement failures
 * - Sampling-rule "Sampled check — this part" badge logic
 * - Kiosk-specific session binding (auto-fill provider)
 *
 * URL: `/operator/steps/$stepId/substeps?part=&workOrder=&execution=&at=`
 */
import { useEffect, useMemo, useState } from "react";
import { useParams, useSearch, useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import {
    Loader2,
    ArrowLeft,
    ArrowRight,
    Check,
    Bug,
    FlaskConical,
    PenLine,
    ListChecks,
    Pencil,
    Ban,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSubsteps, useSubmitSubstep } from "@/hooks/useSubsteps";
import type { Substep } from "@/hooks/useSubsteps";
import { getCookie } from "@/lib/utils";

const csrfHeaders = () => ({ "X-CSRFToken": getCookie("csrftoken") ?? "" });
import {
    OperatorResponseContext,
    type OperatorResponses,
    type OperatorResponseContextValue,
} from "@/components/dwi/shared/OperatorResponseContext";
import {
    PartContext,
    type PartContextValue,
} from "@/components/dwi/shared/PartContext";
import { SubstepOperatorView } from "@/components/dwi/SubstepOperatorView";
import { BatchPanel } from "@/components/dwi/BatchPanel";
import { DecisionResolverPanel } from "@/components/dwi/DecisionResolverPanel";
import { ReworkLimitBanner } from "@/components/dwi/ReworkLimitBanner";
import { FpiStatusBanner } from "@/components/fpi-status-banner";
import { useRetrieveParts, useCompleteStep } from "@/hooks/parts";
import {
    useSamplingDecisionsForExecution,
    buildOutcomeMap,
    type SamplingOutcome,
} from "@/hooks/useSamplingDecisions";
import {
    buildCaptures,
    findMissingRequired,
    summarizeResponses,
} from "@/lib/dwi/build-captures";

type RouteParams = { stepId: string };
type SearchParams = {
    part?: string;
    workOrder?: string;
    /** Receiving inspection: the MaterialLot subject of this execution (no part/WO). */
    material_lot?: string;
    execution?: string;
    at?: number;
    debug?: string;
    /** Comma-separated list of remaining part ids to work in serial after
     *  the current one. Populated by the `StartWorkDialog` when an
     *  operator checks multiple parts; consumed by `handleCompleteStep`
     *  to auto-advance to the next part. Empty/absent = no queue. */
    queue?: string;
};

export function OperatorSubstepRuntimePage() {
    const params = useParams({ strict: false }) as Partial<RouteParams>;
    const search = useSearch({ strict: false }) as Partial<SearchParams>;
    const navigate = useNavigate();
    const stepId = params.stepId;

    const { data, isLoading, isError, error } = useSubsteps(
        stepId ? { step: stepId } : undefined,
    );

    // One response map per substep so each substep submit sees only its own
    // captures. Sealed via "Confirm & next" — the in-memory map is the
    // canonical "what the operator has filled out" until end-of-step server
    // flush.
    const [responsesBySubstepId, setResponsesBySubstepId] = useState<
        Record<string, OperatorResponses>
    >({});

    // Sealed = substep was Confirmed by the operator. Auto-advance + the
    // review screen both key off this set.
    const [confirmedIds, setConfirmedIds] = useState<Set<string>>(new Set());

    // N/A dialog state: when set, opens the reason-picker for the targeted
    // substep. Submit fires `submit_substep` immediately with
    // `marked_not_applicable=true` + the reason code, then advances the
    // operator past the substep.
    const [naDialogSubstepId, setNaDialogSubstepId] = useState<string | null>(null);

    const setResponseFor = (substepId: string, node_id: string, value: unknown) => {
        setResponsesBySubstepId((prev) => ({
            ...prev,
            [substepId]: { ...(prev[substepId] ?? {}), [node_id]: value },
        }));
    };

    // QR ids pre-bound for the inspection-point substeps we've already
    // landed on this session. Keyed by substep id so each inspection
    // point gets its own (part, step)-scoped inspection record. Populated
    // by the eager `ensure_inspection_qr` effect below; consumed by the
    // partContext memo so PartAnnotation et al. can find their bound QR
    // without waiting for substep submit.
    const [qrIdBySubstepId, setQrIdBySubstepId] = useState<Record<string, string>>({});

    // Resolve the active substep id eagerly so the eager-bind effect can
    // run unconditionally (Rules of Hooks: no conditional hook calls).
    // Falls back to undefined while data is loading; the effect bails.
    const rawSubsteps = (data?.results as Substep[] | undefined) ?? [];
    const sortedForBind = useMemo(
        () => [...rawSubsteps].sort((a, b) => a.order - b.order),
        [rawSubsteps],
    );
    const rawAtBind = Number(search.at ?? 0);
    const atBind = Number.isFinite(rawAtBind)
        ? Math.max(0, Math.min(rawAtBind, sortedForBind.length))
        : 0;
    const activeSubstep =
        atBind < sortedForBind.length ? sortedForBind[atBind] : undefined;
    const activeSubstepId = activeSubstep?.id;
    const activeIsInspectionPoint = Boolean(activeSubstep?.is_inspection_point);

    // Eagerly pre-bind a QualityReports row when the operator lands on an
    // inspection-point substep. PartAnnotation (and other QR-aware capture
    // nodes) need the QR id *before* substep submit so they can attach
    // findings to it as the operator works. The endpoint is idempotent —
    // re-calls return the same row.
    useEffect(() => {
        if (!activeSubstepId || !activeIsInspectionPoint) return;
        if (!search.execution) return; // can't bind without a step_execution
        if (qrIdBySubstepId[activeSubstepId]) return; // already bound
        let cancelled = false;
        // Raw fetch instead of the generated client: spectacular infers the
        // body type from the default SubstepRequest serializer, but this
        // action's real body is just `{ step_execution: <uuid> }`. Zodios
        // would reject the simplified payload.
        fetch(`/api/Substeps/${activeSubstepId}/ensure_inspection_qr/`, {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/json",
                ...csrfHeaders(),
            },
            body: JSON.stringify({ step_execution: search.execution }),
        })
            .then((r) => (r.ok ? r.json() : Promise.reject(r)))
            .then((resp: { quality_report_id?: string }) => {
                if (cancelled) return;
                const qrId = resp?.quality_report_id;
                if (qrId) {
                    setQrIdBySubstepId((prev) =>
                        prev[activeSubstepId] === qrId
                            ? prev
                            : { ...prev, [activeSubstepId]: qrId },
                    );
                }
            })
            .catch((err: unknown) => {
                console.error("ensure_inspection_qr failed:", err);
            });
        return () => {
            cancelled = true;
        };
    }, [activeSubstepId, activeIsInspectionPoint, search.execution, qrIdBySubstepId]);

    const submit = useSubmitSubstep();
    const completeStep = useCompleteStep();

    // SamplingDecisions for this StepExecution. Called unconditionally to
    // satisfy Rules of Hooks; the query is `enabled` only when an execution
    // id is present, so a missing exec is a cheap no-op.
    const { data: decisionsData } = useSamplingDecisionsForExecution(
        search.execution ?? "",
    );
    const outcomeBySubstepId = useMemo(
        () => buildOutcomeMap(decisionsData?.results),
        [decisionsData],
    );

    // Cohort parts at this (WO, Step) — fuels the BatchPanel's "Start
    // batch with cohort" action. Enabled only when both ids are present.
    const cohortQueryEnabled = Boolean(search.workOrder && stepId);
    const { data: cohortPartsData } = useRetrieveParts(
        cohortQueryEnabled
            // exclude_terminal: a scrapped/cancelled/shipped part sitting at the
            // step is not live work and must not be selectable into a load.
            ? { work_order: search.workOrder, step: stepId, exclude_terminal: true, limit: 500 }
            : undefined,
        undefined,
        { enabled: cohortQueryEnabled },
    );
    const cohortParts = useMemo(
        () =>
            (cohortPartsData?.results ?? [])
                .filter((p) => !p.split_from_cohort)
                .map((p) => ({ id: String(p.id), label: p.ERP_id ?? String(p.id).slice(0, 8) })),
        [cohortPartsData],
    );
    // A >500-part cohort would silently truncate the batch-start list (§3.10);
    // surface it so the operator never starts a load on a partial cohort.
    const cohortTruncated = Boolean(
        cohortPartsData &&
            (cohortPartsData.count ?? 0) > (cohortPartsData.results?.length ?? 0),
    );

    if (!stepId) {
        return <MissingStepIdScreen />;
    }
    if (isLoading) {
        return <LoadingScreen />;
    }
    if (isError) {
        return <ErrorScreen error={error} />;
    }

    const substeps: Substep[] = (data?.results as Substep[] | undefined) ?? [];
    const sortedSubsteps = [...substeps].sort((a, b) => a.order - b.order);
    if (sortedSubsteps.length === 0) {
        // A step can legitimately have no substeps — most commonly a pure
        // decision point (routing, no work to instruct). Still render the
        // runtime banners (they self-hide when not applicable) so a decision
        // point shows its resolver and a capped step shows its rework status,
        // rather than dead-ending on the "author substeps" prompt.
        return (
            <div className="flex h-full min-h-0 flex-col bg-background operator-runtime">
                <main className="flex min-h-0 flex-1 justify-center overflow-auto p-6">
                    <div className="w-full max-w-3xl space-y-4">
                        {search.workOrder && (
                            <FpiStatusBanner workOrderId={search.workOrder} stepId={stepId} />
                        )}
                        {search.part && <ReworkLimitBanner partId={search.part} />}
                        {search.part && (
                            <DecisionResolverPanel
                                partId={search.part}
                                onResolved={() =>
                                    advanceToNextQueuedPart({
                                        queue: search.queue ?? "",
                                        workOrderId: search.workOrder ?? null,
                                        navigate,
                                    })
                                }
                            />
                        )}
                        <EmptyStepScreen />
                    </div>
                </main>
            </div>
        );
    }


    // Index 0..n-1 selects a substep; index n is the end-of-step review.
    const rawAt = Number(search.at ?? 0);
    const at = Number.isFinite(rawAt) ? Math.max(0, Math.min(rawAt, sortedSubsteps.length)) : 0;
    const isReview = at >= sortedSubsteps.length;
    const current = isReview ? null : sortedSubsteps[at];

    const goTo = (idx: number) => {
        navigate({
            to: "/operator/steps/$stepId/substeps",
            params: { stepId },
            search: { ...search, at: idx },
        });
    };

    const totalCaptures = Object.values(responsesBySubstepId).reduce(
        (n, m) => n + Object.keys(m).length,
        0,
    );

    const partContext: PartContextValue = {
        part_id: search.part ?? null,
        work_order_id: search.workOrder ?? null,
        step_execution_id: search.execution ?? null,
        quality_report_id: current ? (qrIdBySubstepId[current.id] ?? null) : null,
    };

    return (
        <PartContext.Provider value={partContext}>
            <div className="flex h-full min-h-0 flex-col bg-background operator-runtime">
                <ProgressRail
                    substeps={sortedSubsteps}
                    currentIdx={at}
                    confirmedIds={confirmedIds}
                    outcomeBySubstepId={outcomeBySubstepId}
                    onJump={goTo}
                />

                <main className="flex min-h-0 flex-1 justify-center overflow-auto p-6">
                    <div className="w-full max-w-3xl space-y-4">
                        {search.workOrder && (
                            <FpiStatusBanner workOrderId={search.workOrder} stepId={stepId} />
                        )}
                        {search.part && <ReworkLimitBanner partId={search.part} />}
                        {search.part && (
                            <DecisionResolverPanel
                                partId={search.part}
                                onResolved={() =>
                                    advanceToNextQueuedPart({
                                        queue: search.queue ?? "",
                                        workOrderId: search.workOrder ?? null,
                                        navigate,
                                    })
                                }
                            />
                        )}
                        {sortedSubsteps.some((s) => s.scope === "batch") && search.workOrder && (
                            <BatchPanel
                                workOrderId={search.workOrder}
                                stepId={stepId}
                                cohortParts={cohortParts}
                                cohortTruncated={cohortTruncated}
                            />
                        )}
                        {isReview ? (
                            <ReviewStage
                                substeps={sortedSubsteps}
                                responsesBySubstepId={responsesBySubstepId}
                                outcomeBySubstepId={outcomeBySubstepId}
                                onEdit={(idx) => goTo(idx)}
                                onCompleteStep={() => {
                                    handleCompleteStep({
                                        substeps: sortedSubsteps,
                                        responsesBySubstepId,
                                        stepExecutionId: search.execution ?? null,
                                        partId: search.part ?? null,
                                        workOrderId: search.workOrder ?? null,
                                        materialLotId: search.material_lot ?? null,
                                        queue: search.queue ?? "",
                                        navigate,
                                        submit,
                                        completeStep,
                                    });
                                }}
                                completing={submit.isPending || completeStep.isPending}
                                stepExecutionAvailable={Boolean(search.execution)}
                            />
                        ) : current ? (
                            <SubstepStage
                                substep={current}
                                responses={responsesBySubstepId[current.id] ?? {}}
                                setResponse={(node_id, value) => setResponseFor(current.id, node_id, value)}
                                outcome={outcomeBySubstepId[current.id]}
                                onMarkNotApplicable={() => setNaDialogSubstepId(current.id)}
                            />
                        ) : null}
                    </div>
                </main>

                {!isReview && current && (
                    <ActionBar
                        substep={current}
                        responses={responsesBySubstepId[current.id] ?? {}}
                        isFirst={at === 0}
                        isLast={at === sortedSubsteps.length - 1}
                        outcome={outcomeBySubstepId[current.id]}
                        onBack={() => goTo(at - 1)}
                        onConfirm={() => {
                            setConfirmedIds((prev) => new Set(prev).add(current.id));
                            goTo(at + 1);
                        }}
                    />
                )}

                {search.debug === "1" && (
                    <DebugPane
                        responsesBySubstepId={responsesBySubstepId}
                        totalCaptures={totalCaptures}
                    />
                )}

                <NotApplicableDialog
                    open={naDialogSubstepId !== null}
                    substep={
                        naDialogSubstepId
                            ? sortedSubsteps.find((s) => s.id === naDialogSubstepId) ?? null
                            : null
                    }
                    pending={submit.isPending}
                    onCancel={() => setNaDialogSubstepId(null)}
                    onConfirm={(reasonCode) => {
                        if (!naDialogSubstepId || !search.execution) {
                            setNaDialogSubstepId(null);
                            return;
                        }
                        const targetIdx = sortedSubsteps.findIndex((s) => s.id === naDialogSubstepId);
                        submit.mutate(
                            {
                                id: naDialogSubstepId,
                                data: {
                                    step_execution: search.execution,
                                    captures: [],
                                    marked_not_applicable: true,
                                    na_reason_code: reasonCode,
                                },
                            },
                            {
                                onSuccess: () => {
                                    setConfirmedIds((prev) =>
                                        new Set(prev).add(naDialogSubstepId),
                                    );
                                    setNaDialogSubstepId(null);
                                    toast.success("Marked not applicable");
                                    if (targetIdx >= 0) goTo(targetIdx + 1);
                                },
                                onError: (err: unknown) => {
                                    const msg =
                                        (err as { response?: { data?: { detail?: string } } })
                                            ?.response?.data?.detail ??
                                        "Could not mark not applicable.";
                                    toast.error(msg);
                                },
                            },
                        );
                    }}
                />
            </div>
        </PartContext.Provider>
    );
}

// ============================================================================
// N/A reason dialog
// ============================================================================

/**
 * Reason-coded N/A modal.
 *
 * Common reasons are exposed as pick chips so operators don't have to type
 * for routine cases; a free-text fallback covers the edge cases. Server
 * re-validates the reason code at submit time — empty / whitespace-only
 * reasons get rejected at the API boundary.
 */
const COMMON_NA_REASONS: { code: string; label: string }[] = [
    { code: "not_in_revision", label: "Not in this revision" },
    { code: "not_applicable_geometry", label: "Doesn't apply to this geometry" },
    { code: "feature_not_present", label: "Feature not present on this part" },
    { code: "previously_inspected", label: "Already inspected upstream" },
    { code: "engineering_disposition", label: "Engineering disposition" },
];

function NotApplicableDialog({
    open,
    substep,
    pending,
    onCancel,
    onConfirm,
}: {
    open: boolean;
    substep: Substep | null;
    pending: boolean;
    onCancel: () => void;
    onConfirm: (reasonCode: string) => void;
}) {
    const [reasonCode, setReasonCode] = useState("");
    useEffect(() => {
        if (!open) setReasonCode("");
    }, [open]);

    const submit = () => {
        const trimmed = reasonCode.trim();
        if (!trimmed) return;
        onConfirm(trimmed);
    };

    return (
        <Dialog
            open={open}
            onOpenChange={(next) => {
                if (!next) onCancel();
            }}
        >
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Mark not applicable</DialogTitle>
                </DialogHeader>
                <div className="space-y-3">
                    <p className="text-sm text-muted-foreground">
                        Recording N/A for{" "}
                        <span className="font-medium">
                            {substep?.title || "this substep"}
                        </span>
                        . Pick a reason or type your own — the code lands in the
                        audit trail.
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                        {COMMON_NA_REASONS.map((r) => (
                            <Button
                                key={r.code}
                                variant={reasonCode === r.code ? "default" : "outline"}
                                size="sm"
                                className="h-7 text-xs"
                                onClick={() => setReasonCode(r.code)}
                            >
                                {r.label}
                            </Button>
                        ))}
                    </div>
                    <div className="space-y-1">
                        <Label htmlFor="na-reason" className="text-xs">
                            Reason code
                        </Label>
                        <Input
                            id="na-reason"
                            value={reasonCode}
                            onChange={(e) => setReasonCode(e.target.value)}
                            placeholder="snake_case_reason"
                            className="h-9 font-mono text-sm"
                            autoFocus
                        />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="ghost" onClick={onCancel} disabled={pending}>
                        Cancel
                    </Button>
                    <Button onClick={submit} disabled={pending || !reasonCode.trim()}>
                        {pending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Mark N/A
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

// ============================================================================
// Top progress rail
// ============================================================================

function ProgressRail({
    substeps,
    currentIdx,
    confirmedIds,
    outcomeBySubstepId,
    onJump,
}: {
    substeps: Substep[];
    currentIdx: number;
    confirmedIds: Set<string>;
    outcomeBySubstepId: Record<string, SamplingOutcome>;
    onJump: (idx: number) => void;
}) {
    const reviewIdx = substeps.length;
    const sampledOutCount = substeps.filter(
        (s) => outcomeBySubstepId[s.id] === "deselected",
    ).length;
    return (
        <div className="shrink-0 border-b bg-background px-6 py-3">
            <div className="mb-2 flex items-baseline justify-between">
                <div className="text-sm font-medium">
                    Step ·{" "}
                    <span className="text-muted-foreground">
                        {currentIdx >= reviewIdx
                            ? "Review"
                            : `${currentIdx + 1} of ${substeps.length}`}
                    </span>
                </div>
                <div className="text-xs text-muted-foreground">
                    {confirmedIds.size} of {substeps.length} confirmed
                    {sampledOutCount > 0 && (
                        <span className="ml-2">· {sampledOutCount} not in sample</span>
                    )}
                </div>
            </div>
            <div className="flex items-center gap-1">
                {substeps.map((s, i) => {
                    const isConfirmed = confirmedIds.has(s.id);
                    const isCurrent = i === currentIdx;
                    const outcome = outcomeBySubstepId[s.id];
                    const isDeselected = outcome === "deselected";
                    return (
                        <button
                            key={s.id}
                            type="button"
                            onClick={() => onJump(i)}
                            title={`${i + 1}. ${s.title}${isDeselected ? " — not in sample" : ""}`}
                            className={`h-2 flex-1 rounded-full transition ${
                                isCurrent
                                    ? "bg-primary"
                                    : isConfirmed
                                        ? "bg-green-500"
                                        : isDeselected
                                            ? "bg-muted-foreground/20 hover:bg-muted-foreground/40"
                                            : "bg-muted hover:bg-muted-foreground/30"
                            }`}
                            aria-label={`Jump to substep ${i + 1}: ${s.title}`}
                        />
                    );
                })}
                <button
                    type="button"
                    onClick={() => onJump(reviewIdx)}
                    title="End-of-step review"
                    className={`h-2 w-8 rounded-full transition ${
                        currentIdx === reviewIdx
                            ? "bg-primary"
                            : "bg-muted hover:bg-muted-foreground/30"
                    }`}
                    aria-label="Jump to review"
                />
            </div>
        </div>
    );
}

// ============================================================================
// Substep stage — one substep, full attention
// ============================================================================

function SubstepStage({
    substep,
    responses,
    setResponse,
    outcome,
    onMarkNotApplicable,
}: {
    substep: Substep;
    responses: OperatorResponses;
    setResponse: (node_id: string, value: unknown) => void;
    outcome?: SamplingOutcome;
    onMarkNotApplicable?: () => void;
}) {
    const contextValue = useMemo<OperatorResponseContextValue>(
        () => ({ responses, setResponse }),
        [responses, setResponse],
    );
    const isDeselected = outcome === "deselected";
    const isPending = outcome === "pending";
    return (
        <div className="rounded-lg border bg-card shadow-sm">
            <div className="flex items-center gap-3 border-b px-6 py-4">
                <span
                    className={
                        "text-2xl font-semibold tracking-tight " +
                        (isDeselected ? "text-muted-foreground" : "")
                    }
                >
                    {substep.title || "Untitled substep"}
                </span>
                <div className="ml-auto flex items-center gap-1.5">
                    {isDeselected ? (
                        <Badge variant="outline" className="border-muted-foreground/40 text-muted-foreground">
                            Not in sample
                        </Badge>
                    ) : (
                        <>
                            {!substep.is_optional && (
                                <Badge variant="secondary">Required</Badge>
                            )}
                            {substep.is_optional && (
                                <Badge variant="outline">Optional</Badge>
                            )}
                            {isPending && (
                                <Badge variant="outline" className="border-amber-500/60 text-amber-600">
                                    Pending sample
                                </Badge>
                            )}
                            {substep.is_critical && (
                                <Badge className="bg-destructive text-destructive-foreground">
                                    Critical
                                </Badge>
                            )}
                            {substep.is_inspection_point && (
                                <Badge className="bg-amber-600 text-white">
                                    <FlaskConical className="mr-1 h-3 w-3" /> Inspection point
                                </Badge>
                            )}
                            {substep.requires_signature && (
                                <Badge variant="outline">
                                    <PenLine className="mr-1 h-3 w-3" /> Sign-off
                                </Badge>
                            )}
                            {substep.allow_not_applicable && !substep.is_critical && onMarkNotApplicable && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={onMarkNotApplicable}
                                    className="h-7 text-xs text-muted-foreground hover:text-foreground"
                                    title="Mark this substep as not applicable to this part (reason required)."
                                >
                                    <Ban className="mr-1 h-3.5 w-3.5" />
                                    Not applicable
                                </Button>
                            )}
                        </>
                    )}
                </div>
            </div>
            {isDeselected ? (
                <div className="px-6 py-8 text-center text-sm text-muted-foreground">
                    <p className="font-medium">This substep is not in your sample.</p>
                    <p className="mt-1 text-xs">
                        The sampling rule excluded this part from the check —
                        skip to the next substep.
                    </p>
                </div>
            ) : (
                <OperatorResponseContext.Provider value={contextValue}>
                    <SubstepOperatorView
                        body={(substep.body_blocks as unknown as object) ?? { type: "doc", content: [] }}
                    />
                </OperatorResponseContext.Provider>
            )}
        </div>
    );
}

// ============================================================================
// Bottom action bar
// ============================================================================

function ActionBar({
    substep,
    responses,
    isFirst,
    isLast,
    outcome,
    onBack,
    onConfirm,
}: {
    substep: Substep;
    responses: OperatorResponses;
    isFirst: boolean;
    isLast: boolean;
    outcome?: SamplingOutcome;
    onBack: () => void;
    onConfirm: () => void;
}) {
    const captureCount = Object.keys(responses).length;
    const isDeselected = outcome === "deselected";
    const missing = useMemo(
        () =>
            isDeselected
                ? []
                : findMissingRequired(substep.body_blocks as unknown as object, responses),
        [substep.body_blocks, responses, isDeselected],
    );
    const blocked = missing.length > 0;

    /** Confirm-tap behavior — when something is missing, scroll the first
     *  incomplete capture into view and pulse it briefly. Button stays
     *  enabled (per design rec: never silently disable, operators stare
     *  at a dead button and don't know why). When nothing's missing,
     *  fires the real confirm. */
    const handleConfirmAttempt = () => {
        if (!blocked) {
            onConfirm();
            return;
        }
        const first = missing[0];
        const el = document.querySelector<HTMLElement>(
            `[data-node-id="${cssEscape(first.node_id)}"]`,
        );
        if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
            // Trigger the keyframe by re-applying the class — remove then add
            // after the next frame so a repeat tap pulses again.
            el.classList.remove("dwi-pulse-missing");
            void el.offsetWidth; // force reflow
            el.classList.add("dwi-pulse-missing");
            window.setTimeout(() => el.classList.remove("dwi-pulse-missing"), 1500);
        }
    };

    return (
        <div className="shrink-0 border-t bg-background/95 backdrop-blur px-6 py-4">
            <div className="mx-auto flex w-full max-w-3xl items-center gap-3">
                <Button
                    variant="ghost"
                    size="lg"
                    onClick={onBack}
                    disabled={isFirst}
                    className="h-14 min-w-32"
                >
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                </Button>
                <div className="flex-1 text-center text-xs">
                    {isDeselected ? (
                        <span className="text-muted-foreground">
                            Not in sample — skip to the next substep
                        </span>
                    ) : blocked ? (
                        <span className="text-amber-600">
                            {missing.length === 1
                                ? `1 required field missing: ${missing[0].label}`
                                : `${missing.length} required fields missing — ${missing
                                      .slice(0, 2)
                                      .map((m) => m.label)
                                      .join(", ")}${missing.length > 2 ? ", …" : ""}`}
                        </span>
                    ) : captureCount > 0 ? (
                        <span className="text-muted-foreground">
                            {captureCount} field{captureCount === 1 ? "" : "s"} captured
                        </span>
                    ) : (
                        <span className="text-muted-foreground">
                            {substep.is_optional
                                ? "Nothing captured — you can still continue"
                                : "Ready to continue"}
                        </span>
                    )}
                </div>
                <Button
                    size="lg"
                    onClick={isDeselected ? onConfirm : handleConfirmAttempt}
                    title={
                        blocked
                            ? `Tap to scroll to: ${missing.map((m) => m.label).join(", ")}`
                            : undefined
                    }
                    variant={isDeselected ? "secondary" : "default"}
                    className="h-14 min-w-52 text-base font-semibold"
                >
                    {isDeselected ? (
                        <>Skip & next <ArrowRight className="ml-2 h-4 w-4" /></>
                    ) : (
                        <>
                            <Check className="mr-2 h-5 w-5" />
                            {isLast ? "Confirm & review" : "Confirm & next"}
                            <ArrowRight className="ml-2 h-4 w-4" />
                        </>
                    )}
                </Button>
            </div>
        </div>
    );
}

/** Minimal CSS.escape polyfill for node_ids that contain special chars.
 *  Modern browsers all have CSS.escape; this stub keeps us safe in old
 *  environments without bloating the bundle. */
function cssEscape(s: string): string {
    if (typeof CSS !== "undefined" && typeof CSS.escape === "function") {
        return CSS.escape(s);
    }
    return s.replace(/(["\\])/g, "\\$1");
}

// ============================================================================
// End-of-step review
// ============================================================================

function ReviewStage({
    substeps,
    responsesBySubstepId,
    outcomeBySubstepId,
    onEdit,
    onCompleteStep,
    completing,
    stepExecutionAvailable,
}: {
    substeps: Substep[];
    responsesBySubstepId: Record<string, OperatorResponses>;
    outcomeBySubstepId: Record<string, SamplingOutcome>;
    onEdit: (idx: number) => void;
    onCompleteStep: () => void;
    completing: boolean;
    stepExecutionAvailable: boolean;
}) {
    return (
        <div className="space-y-4">
            <div>
                <h1 className="text-2xl font-semibold tracking-tight">
                    Review captures
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    Confirm the captures look right, then complete the step.
                </p>
            </div>
            <div className="space-y-3">
                {substeps.map((s, idx) => {
                    const responses = responsesBySubstepId[s.id] ?? {};
                    const outcome = outcomeBySubstepId[s.id];
                    const isDeselected = outcome === "deselected";
                    const summary = summarizeResponses(
                        s.body_blocks as unknown as object,
                        responses,
                    );
                    const filled = summary.filter((r) => !r.empty);
                    const missing = isDeselected
                        ? []
                        : findMissingRequired(
                            s.body_blocks as unknown as object,
                            responses,
                          );
                    return (
                        <div
                            key={s.id}
                            className={
                                "rounded-md border bg-card " +
                                (isDeselected ? "opacity-60" : "")
                            }
                        >
                            <div className="flex items-center gap-3 border-b px-4 py-3">
                                <span className="w-6 shrink-0 text-sm font-medium text-muted-foreground tabular-nums">
                                    {idx + 1}.
                                </span>
                                <span className="flex-1 text-sm font-medium">
                                    {s.title}
                                </span>
                                {isDeselected ? (
                                    <Badge
                                        variant="outline"
                                        className="border-muted-foreground/40 text-[10px] text-muted-foreground"
                                    >
                                        Not in sample
                                    </Badge>
                                ) : (
                                    <Badge
                                        variant={filled.length > 0 ? "secondary" : "outline"}
                                        className="text-[10px]"
                                    >
                                        <ListChecks className="mr-1 h-3 w-3" />
                                        {filled.length} of {summary.length}
                                    </Badge>
                                )}
                                {s.is_inspection_point && !isDeselected && (
                                    <Badge className="bg-amber-600 text-[10px] text-white">
                                        Inspection
                                    </Badge>
                                )}
                                {missing.length > 0 && (
                                    <Badge variant="destructive" className="text-[10px]">
                                        {missing.length} required missing
                                    </Badge>
                                )}
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => onEdit(idx)}
                                    className="h-8"
                                >
                                    <Pencil className="mr-1.5 h-3.5 w-3.5" />
                                    Edit
                                </Button>
                            </div>
                            {isDeselected ? (
                                <div className="px-4 py-2 text-xs italic text-muted-foreground">
                                    Sampling rule excluded this part — nothing to capture.
                                </div>
                            ) : summary.length === 0 ? (
                                <div className="px-4 py-2 text-xs italic text-muted-foreground">
                                    No capture nodes in this substep.
                                </div>
                            ) : (
                                <dl className="divide-y text-sm">
                                    {summary.map((row) => (
                                        <div
                                            key={row.node_id}
                                            className="flex items-baseline gap-3 px-4 py-2"
                                        >
                                            <dt className="w-48 shrink-0 text-xs text-muted-foreground">
                                                {row.label}
                                            </dt>
                                            <dd
                                                className={
                                                    "flex-1 font-mono text-sm " +
                                                    (row.empty
                                                        ? "text-muted-foreground/60"
                                                        : "text-foreground")
                                                }
                                            >
                                                {row.display}
                                            </dd>
                                        </div>
                                    ))}
                                </dl>
                            )}
                        </div>
                    );
                })}
            </div>
            <div className="flex items-center justify-end gap-3 border-t pt-4">
                {!stepExecutionAvailable && (
                    <span className="text-xs text-amber-600">
                        {"Add `?execution=<id>` to the URL to enable submit."}
                    </span>
                )}
                <Button
                    size="lg"
                    className="h-14 min-w-56 text-base font-semibold"
                    disabled={!stepExecutionAvailable || completing}
                    onClick={onCompleteStep}
                >
                    {completing ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                        <Check className="mr-2 h-5 w-5" />
                    )}
                    Complete step
                </Button>
            </div>
        </div>
    );
}

// ============================================================================
// Completion — fan out submit calls in order
// ============================================================================

async function handleCompleteStep({
    substeps,
    responsesBySubstepId,
    stepExecutionId,
    partId,
    workOrderId,
    materialLotId,
    queue,
    navigate,
    submit,
    completeStep,
}: {
    substeps: Substep[];
    responsesBySubstepId: Record<string, OperatorResponses>;
    stepExecutionId: string | null;
    partId: string | null;
    workOrderId: string | null;
    /** Receiving inspection: the MaterialLot subject, when this isn't a part run. */
    materialLotId: string | null;
    /** Comma-separated remaining part ids to work in serial after this one. */
    queue: string;
    navigate: ReturnType<typeof useNavigate>;
    submit: ReturnType<typeof useSubmitSubstep>;
    completeStep: ReturnType<typeof useCompleteStep>;
}) {
    if (!stepExecutionId) {
        toast.error("Missing step_execution", {
            description: "Add `?execution=<id>` to the URL to enable submit.",
        });
        return;
    }
    // Phase 1: flush per-substep captures.
    let okCount = 0;
    let failCount = 0;
    for (const s of substeps) {
        const responses = responsesBySubstepId[s.id] ?? {};
        if (Object.keys(responses).length === 0) continue;
        const captures = buildCaptures(s.body_blocks as unknown as object, responses);
        try {
            await submit.mutateAsync({
                id: s.id,
                data: { step_execution: stepExecutionId, captures },
            });
            okCount++;
        } catch {
            failCount++;
        }
    }
    if (failCount > 0) {
        toast.error("Some substeps failed to submit", {
            description: `${okCount} succeeded, ${failCount} failed. Retry from the review screen.`,
        });
        return;
    }

    // Receiving inspection (MaterialLot subject): captures are saved; the
    // accept/reject disposition lives on the receiving inspection page, so
    // route the operator back there to finish.
    if (!partId && materialLotId) {
        toast.success("Inspection captures saved", {
            description: "Accept or reject the lot to finish.",
        });
        navigate({
            to: "/production/receiving-inspection/$lotId",
            params: { lotId: materialLotId },
        });
        return;
    }

    // Phase 2: THE advancement trigger. Synchronously run the gate via
    // `complete_step` and surface the result. The captures are already
    // persisted; this call decides whether the part / lot can advance.
    if (!partId) {
        toast("Captures submitted", {
            description: "Add `?part=<id>` to the URL to trigger advancement.",
        });
        return;
    }
    try {
        const result = await completeStep.mutateAsync(partId);
        if (result.status === "advanced") {
            const advanced = [
                ...(result.parts_advanced ?? []),
                ...(result.split_parts_advanced ?? []),
            ];
            toast.success(`Step complete — lot advanced (${advanced.length} part${advanced.length === 1 ? "" : "s"} moved).`);
        } else if (result.status === "blocked") {
            const blockers = result.blockers_by_part ?? {};
            const reasons = new Set<string>();
            Object.values(blockers).forEach((list) =>
                (list as string[]).forEach((r) => reasons.add(r)),
            );
            toast.warning("Step submitted — lot waiting on cohort", {
                description: reasons.size > 0
                    ? [...reasons].slice(0, 3).join("; ")
                    : "Other parts in the cohort still have work to do.",
            });
        } else if (result.status === "halted") {
            toast.error("Lot halted", { description: result.reason ?? "" });
        } else {
            toast.success("Step submitted");
        }

        // Serial queue: if more parts were checked in StartWorkDialog, jump
        // to the next one. We ensure that part's StepExecution here
        // (rather than prefetching on dialog Start) so this click is the
        // only place that owns the get-or-create.
        await advanceToNextQueuedPart({ queue, workOrderId, navigate });
    } catch {
        toast.error("Couldn't run advancement", {
            description: "Captures saved; advancement will retry on the next event.",
        });
    }
}

/** Advance the operator to the next part in the StartWorkDialog queue.
 *  No-op when the queue is empty or essential context is missing. */
async function advanceToNextQueuedPart({
    queue,
    workOrderId,
    navigate,
}: {
    queue: string;
    workOrderId: string | null;
    navigate: ReturnType<typeof useNavigate>;
}) {
    if (!queue || !workOrderId) return;
    const ids = queue.split(",").filter(Boolean);
    if (ids.length === 0) return;

    const [nextPartId, ...rest] = ids;

    // Look up the next part's current step so we know where to route. The
    // part may have been advanced or split since dialog open, so we read
    // current state rather than trusting the dialog snapshot.
    let nextStepId: string | null = null;
    try {
        const r = await fetch(`/api/Parts/${nextPartId}/`, { credentials: "include" });
        if (r.ok) {
            const part = await r.json();
            if (part?.step) nextStepId = String(part.step);
        }
    } catch {
        // network/auth blip — fall through, toast below
    }
    if (!nextStepId) {
        toast.warning("Next queued part isn't at a routable step — skipping the rest", {
            description: `${ids.length} part${ids.length === 1 ? "" : "s"} remaining in your queue.`,
        });
        return;
    }

    // Ensure StepExecution for the next part. Mirrors the
    // `useEnsureStepExecution` hook but inline since this isn't React-render-time.
    let executionId: string | null = null;
    try {
        const listUrl =
            `/api/StepExecutions/?part=${encodeURIComponent(nextPartId)}` +
            `&step=${encodeURIComponent(nextStepId)}&limit=1`;
        const lr = await fetch(listUrl, { credentials: "include" });
        const ld = await lr.json();
        const existing = ld?.results?.[0];
        if (existing?.id) {
            executionId = String(existing.id);
        } else {
            const csrf = document.cookie
                .split(";")
                .map((c) => c.trim())
                .find((c) => c.startsWith("csrftoken="))
                ?.split("=")[1] ?? "";
            const cr = await fetch("/api/StepExecutions/", {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
                body: JSON.stringify({
                    part: nextPartId,
                    step: nextStepId,
                    status: "IN_PROGRESS",
                }),
            });
            if (cr.ok) {
                const created = await cr.json();
                if (created?.id) executionId = String(created.id);
            }
        }
    } catch {
        // fall through
    }
    if (!executionId) {
        toast.error("Could not open the next queued part — try Start Work again.");
        return;
    }

    toast.info(`Moving to next part (${ids.length - 1} remaining)`);
    navigate({
        to: "/operator/steps/$stepId/substeps",
        params: { stepId: nextStepId },
        search: {
            part: nextPartId,
            workOrder: workOrderId,
            execution: executionId,
            at: 0,
            ...(rest.length > 0 ? { queue: rest.join(",") } : {}),
        },
    });
}

// ============================================================================
// Misc screens
// ============================================================================

function MissingStepIdScreen() {
    return (
        <div className="p-6">
            <h1 className="text-xl font-semibold">Operator runtime</h1>
            <p className="mt-2 text-sm text-muted-foreground">
                Missing stepId. Navigate to{" "}
                <code className="font-mono text-xs">
                    /operator/steps/$stepId/substeps?part=&lt;id&gt;&amp;execution=&lt;id&gt;
                </code>
                .
            </p>
        </div>
    );
}

function LoadingScreen() {
    return (
        <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading substeps…
        </div>
    );
}

function ErrorScreen({ error }: { error: unknown }) {
    return (
        <div className="m-6 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
            Failed to load substeps: {String(error)}
        </div>
    );
}

function EmptyStepScreen() {
    return (
        <div className="m-6 rounded-md border bg-muted/30 p-6 text-center text-sm text-muted-foreground">
            <Bug className="mx-auto mb-2 h-6 w-6 opacity-60" />
            No substeps configured for this Step yet. Ask an engineer to author them.
        </div>
    );
}

// ============================================================================
// Optional debug pane (only when `?debug=1`)
// ============================================================================

function DebugPane({
    responsesBySubstepId,
    totalCaptures,
}: {
    responsesBySubstepId: Record<string, OperatorResponses>;
    totalCaptures: number;
}) {
    const [collapsed, setCollapsed] = useState(true);
    useEffect(() => {
        // Keyboard shortcut: D to toggle the dev pane.
        const handler = (e: KeyboardEvent) => {
            if (e.key.toLowerCase() === "d" && (e.metaKey || e.ctrlKey) && e.altKey) {
                setCollapsed((v) => !v);
            }
        };
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, []);
    if (collapsed) {
        return (
            <button
                type="button"
                onClick={() => setCollapsed(false)}
                className="fixed bottom-2 right-2 z-50 rounded border bg-background/80 px-2 py-1 text-[10px] font-mono text-muted-foreground shadow"
                title="Show debug pane (Ctrl/Cmd+Alt+D)"
            >
                debug · {totalCaptures}
            </button>
        );
    }
    return (
        <div className="fixed bottom-0 right-0 z-50 m-2 max-h-[40vh] w-[420px] overflow-auto rounded border bg-background/95 p-2 font-mono text-[10px] shadow-lg">
            <div className="mb-1 flex items-center justify-between">
                <span className="font-semibold">debug · captures</span>
                <button
                    type="button"
                    onClick={() => setCollapsed(true)}
                    className="text-muted-foreground hover:text-foreground"
                >
                    ×
                </button>
            </div>
            <pre className="leading-tight">
                {JSON.stringify(responsesBySubstepId, null, 2)}
            </pre>
        </div>
    );
}

export default OperatorSubstepRuntimePage;
