/**
 * DWI completion-stage adapters.
 *
 * The operator runtime (`OperatorSubstepRuntimePage`) is a generic player:
 * walk substeps → capture → review. What differs by context is *what finishing
 * means* — the terminal action. That behaviour is factored here as a set of
 * adapters resolved by subject:
 *
 *   - PART (default): run the advancement gate (`complete_step`), then advance
 *     to the next queued part.
 *   - RECEIVING: the lot acceptance decision + guided disposition happen in the
 *     runtime (unit-by-unit stepper → verdict → accept / reject).
 *
 * New endings (timed batch, reman teardown, FAI, outside processing) plug in as
 * additional adapters — a `matches` predicate plus either a `Footer` (custom
 * end-of-flow UI) or an `onComplete` (terminal action for the generic Complete
 * button). The player never changes.
 */
import { useState, type FC } from "react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import type { useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Check, ArrowRight, Loader2 } from "lucide-react";
import { useSubmitSubstep, type Substep } from "@/hooks/useSubsteps";
import { useCompleteStep } from "@/hooks/parts";
import { ensureStepExecution, TrainingGateError } from "@/hooks/useEnsureStepExecution";
import type { OperatorResponses } from "@/components/dwi/shared/OperatorResponseContext";
import { buildCaptures } from "@/lib/dwi/build-captures";
import {
    ReceivingAcceptanceStage,
    type CapturedMeasurement,
} from "@/components/dwi/ReceivingAcceptanceStage";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Context handed to every adapter
// ---------------------------------------------------------------------------

export type CompletionContext = {
    stepId: string;
    substeps: Substep[];
    responsesBySubstepId: Record<string, OperatorResponses>;
    stepExecutionId: string | null;
    partId: string | null;
    workOrderId: string | null;
    materialLotId: string | null;
    ospShipmentId: string | null;
    queue: string;
    // Receiving unit-by-unit cadence.
    unitMode: boolean;
    unit: number;
    unitCount: number;
    capturedMeasurements: CapturedMeasurement[];
    /** Current URL search, spread when navigating within the same run. */
    search: Record<string, unknown>;
    navigate: ReturnType<typeof useNavigate>;
    submit: ReturnType<typeof useSubmitSubstep>;
    completeStep: ReturnType<typeof useCompleteStep>;
};

export type CompletionAdapter = {
    key: string;
    matches: (ctx: CompletionContext) => boolean;
    /** Custom end-of-flow UI, rendered in place of the generic Complete button. */
    Footer?: FC<{ ctx: CompletionContext }>;
    /** Terminal action for the generic Complete button (adapters without a Footer). */
    onComplete?: (ctx: CompletionContext) => Promise<void> | void;
};

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/** Flush every substep's captures to its inspection record. Returns false if
 *  any substep failed (caller surfaces the error). */
export async function flushSubstepCaptures({
    substeps,
    responsesBySubstepId,
    stepExecutionId,
    submit,
    sampleNumber,
}: {
    substeps: Substep[];
    responsesBySubstepId: Record<string, OperatorResponses>;
    stepExecutionId: string | null;
    submit: ReturnType<typeof useSubmitSubstep>;
    /** Receiving unit-by-unit: tags this unit's measurements (1..n). */
    sampleNumber?: number | null;
}): Promise<boolean> {
    if (!stepExecutionId) return false;
    let failCount = 0;
    for (const s of substeps) {
        const responses = responsesBySubstepId[s.id] ?? {};
        if (Object.keys(responses).length === 0) continue;
        const captures = buildCaptures(s.body_blocks as unknown as object, responses);
        try {
            await submit.mutateAsync({
                id: s.id,
                data: {
                    step_execution: stepExecutionId,
                    captures,
                    ...(sampleNumber != null ? { sample_number: sampleNumber } : {}),
                },
            });
        } catch {
            failCount++;
        }
    }
    return failCount === 0;
}

/** Advance the operator to the next part in the StartWorkDialog queue.
 *  No-op when the queue is empty or essential context is missing. */
export async function advanceToNextQueuedPart({
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

    // Ensure the next part's StepExecution through the SHARED gated path
    // (`ensureStepExecution`) — same competence + reassignment gate as the
    // Start-Work dialog. Previously this was an ungated inline copy that
    // silently reused an existing row, bypassing the gate for the queue flow.
    let executionId: string | null = null;
    try {
        const result = await ensureStepExecution({
            partId: nextPartId,
            stepId: nextStepId,
        });
        executionId = result.executionId;
    } catch (e) {
        if (e instanceof TrainingGateError) {
            // The next queued part is gated for this operator. Stop the queue
            // and send them to Start Work, where the supervisor-override panel
            // lives (we can't collect credentials from here).
            toast.error(
                e.gate.code === "assigned_to_other"
                    ? "Next queued part is assigned to someone else — a supervisor must reassign it."
                    : "You're not qualified for the next queued part — use Start Work to get a supervisor override.",
                { description: `${ids.length} part${ids.length === 1 ? "" : "s"} remaining.` },
            );
            return;
        }
        // fall through to the generic error below
    }
    if (!executionId) {
        toast.error("Could not open the next queued part — try Start Work again.");
        return;
    }

    toast.info(`Moving to next part (${ids.length - 1} remaining)`);
    navigate({
        to: "/operator/steps/$stepId/substeps",
        params: { stepId: nextStepId },
        // Fresh search for the next part — drop the previous part's context
        // (material_lot / unit / osp_shipment) rather than carrying it over.
        search: {
            part: nextPartId,
            workOrder: workOrderId,
            execution: executionId,
            at: 0,
            material_lot: undefined,
            osp_shipment: undefined,
            unit: undefined,
            debug: undefined,
            queue: rest.length > 0 ? rest.join(",") : undefined,
        },
    });
}

// ---------------------------------------------------------------------------
// PART — default completion: advancement gate + serial-queue advance
// ---------------------------------------------------------------------------

async function completePart(ctx: CompletionContext): Promise<void> {
    const { substeps, responsesBySubstepId, stepExecutionId, partId, workOrderId,
        materialLotId, queue, navigate, submit, completeStep } = ctx;

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

    // Receiving inspection (MaterialLot subject) with no Footer path: captures
    // saved, route back to the receiving page to finish. (Normally the
    // RECEIVING adapter's Footer owns this; kept as a defensive fallback.)
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
    // `complete_step` and surface the result.
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

        // Serial queue: jump to the next checked part, if any.
        await advanceToNextQueuedPart({ queue, workOrderId, navigate });
    } catch {
        toast.error("Couldn't run advancement", {
            description: "Captures saved; advancement will retry on the next event.",
        });
    }
}

const PART_COMPLETION: CompletionAdapter = {
    key: "part",
    matches: () => true, // default — resolver tries it last
    onComplete: completePart,
};

// ---------------------------------------------------------------------------
// RECEIVING — lot acceptance + guided disposition, in-runtime
// ---------------------------------------------------------------------------

function ReceivingCompletionFooter({ ctx }: { ctx: CompletionContext }) {
    const [advancing, setAdvancing] = useState(false);
    const moreUnits = ctx.unitMode && ctx.unit < ctx.unitCount;
    const flush = (sampleNumber?: number | null) =>
        flushSubstepCaptures({
            substeps: ctx.substeps,
            responsesBySubstepId: ctx.responsesBySubstepId,
            stepExecutionId: ctx.stepExecutionId,
            submit: ctx.submit,
            sampleNumber,
        });

    if (moreUnits) {
        // More sampled units to read before the verdict — record this one, advance.
        return (
            <div className="flex items-center justify-end gap-3 border-t pt-4">
                <Button
                    size="lg"
                    className="h-14 min-w-64 text-base font-semibold"
                    disabled={advancing}
                    onClick={async () => {
                        setAdvancing(true);
                        const ok = await flush(ctx.unit);
                        if (!ok) { toast.error("Could not record this unit"); setAdvancing(false); return; }
                        ctx.navigate({
                            to: "/operator/steps/$stepId/substeps",
                            params: { stepId: ctx.stepId },
                            search: { ...ctx.search, unit: ctx.unit + 1, at: 0 } as never,
                        });
                    }}
                >
                    {advancing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-5 w-5" />}
                    Record unit {ctx.unit} of {ctx.unitCount} → next unit
                    <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
            </div>
        );
    }

    // Final unit (or single-pass): decide the lot in-runtime.
    return (
        <ReceivingAcceptanceStage
            lotId={ctx.materialLotId as string}
            capturedMeasurements={ctx.capturedMeasurements}
            flushCaptures={() => flush(ctx.unitMode ? ctx.unit : undefined)}
            unitMode={ctx.unitMode}
        />
    );
}

const RECEIVING_COMPLETION: CompletionAdapter = {
    key: "receiving",
    matches: (ctx) => Boolean(ctx.materialLotId),
    Footer: ReceivingCompletionFooter,
};

// ---------------------------------------------------------------------------
// OSP — outside-process return inspection: accept advances the parts, reject
// quarantines them for disposition. Same DWI runtime, shipment as subject.
// ---------------------------------------------------------------------------

function OutsideProcessCompletionFooter({ ctx }: { ctx: CompletionContext }) {
    const [busy, setBusy] = useState<"accept" | "reject" | null>(null);
    const qc = useQueryClient();
    const shipmentId = ctx.ospShipmentId as string;

    const decide = async (decision: "accept" | "reject") => {
        setBusy(decision);
        // Flush the inspector's captures to the shipment's return-inspection report first.
        const ok = await flushSubstepCaptures({
            substeps: ctx.substeps,
            responsesBySubstepId: ctx.responsesBySubstepId,
            stepExecutionId: ctx.stepExecutionId,
            submit: ctx.submit,
        });
        if (!ok) { toast.error("Could not record the inspection"); setBusy(null); return; }
        try {
            const headers = { "X-CSRFToken": getCookie("csrftoken") ?? "" };
            if (decision === "accept") {
                await api.api_OutsideProcessShipments_accept_create(undefined as never, { params: { id: shipmentId }, headers });
                toast.success("Accepted — parts advanced past the outside-process step.");
            } else {
                await api.api_OutsideProcessShipments_reject_create(undefined as never, { params: { id: shipmentId }, headers });
                toast.warning("Rejected — parts quarantined for disposition.");
            }
            // Terminal action moved parts off the OSP surfaces — refresh them before leaving.
            const keys = ["ospReadyToShip", "ospShipments", "parts", "incomingInspection"];
            qc.invalidateQueries({ predicate: (q) => keys.includes(q.queryKey[0] as string) });
            ctx.navigate({ to: "/production/outside-processing" });
        } catch {
            toast.error(`Couldn't ${decision} the shipment.`);
        } finally {
            setBusy(null);
        }
    };

    return (
        <div className="flex items-center justify-end gap-3 border-t pt-4">
            <Button size="lg" variant="outline" className="h-14 min-w-40 text-base"
                disabled={busy !== null} onClick={() => decide("reject")}>
                {busy === "reject" && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Reject
            </Button>
            <Button size="lg" className="h-14 min-w-48 text-base font-semibold"
                disabled={busy !== null} onClick={() => decide("accept")}>
                {busy === "accept" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-5 w-5" />}
                Accept return
            </Button>
        </div>
    );
}

const OSP_COMPLETION: CompletionAdapter = {
    key: "osp",
    matches: (ctx) => Boolean(ctx.ospShipmentId),
    Footer: OutsideProcessCompletionFooter,
};

// ---------------------------------------------------------------------------
// Registry + resolver
// ---------------------------------------------------------------------------

/** Ordered most-specific → default. New endings insert before PART. */
export const COMPLETION_ADAPTERS: CompletionAdapter[] = [
    RECEIVING_COMPLETION,
    OSP_COMPLETION,
    PART_COMPLETION,
];

export function resolveCompletion(ctx: CompletionContext): CompletionAdapter {
    return COMPLETION_ADAPTERS.find((a) => a.matches(ctx)) ?? PART_COMPLETION;
}
