/**
 * Operator-runtime BatchPanel.
 *
 * Surfaces when the current Step has at least one BATCH-scope substep.
 * Every load has three phases (services/dwi/batch_lifecycle, 2026-11-03):
 *   - **Loading**: start a load with a chosen subset of the units at (WO, Step) —
 *     a step can run several loads (furnace/wash/autoclave capacity), membership
 *     disjoint — and do the batch substeps up to the seal point.
 *   - **Running**: sealed — confirming the substep flagged "Seals the load", or
 *     Seal when none is. The machine runs; the operator may walk away.
 *   - **Completed**: back at the load, the substeps after the seal point, then
 *     Complete load — which is where the load's parts advance.
 *
 * BATCH-scope substeps are captured a single time per BatchExecution
 * (not per part): submit posts `{ batch_execution, captures }`, which the
 * backend binds to the batch via a SubstepCompletion.
 */

import { useEffect, useRef, useState } from "react";
import { queryOptions, useQuery, useQueryClient } from "@tanstack/react-query";
import { PartContext } from "@/components/dwi/shared/PartContext";
import { Loader2, Package, Lock, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
    invalidateBatches,
    useBatchesForWoStep,
    useCompleteBatchExecution,
    useCreateBatchExecution,
    useSealBatchExecution,
} from "@/hooks/useBatchExecutions";
import { useSubsteps, useSubmitSubstep, type Substep } from "@/hooks/useSubsteps";
import { useSignaturePrompt } from "@/components/dwi/useSignaturePrompt";
import { submitSignedSubstep } from "@/lib/dwi/signed-submit";
import { SubstepOperatorView } from "@/components/dwi/SubstepOperatorView";
import {
    OperatorResponseContext,
    type OperatorResponses,
} from "@/components/dwi/shared/OperatorResponseContext";
import { buildCaptures, findMissingRequired } from "@/lib/dwi/build-captures";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { api } from "@/lib/api/generated";
import { batchCompletionsOptions } from "@/components/dwi/StepCompletionsList";
import { useDraftAutosave } from "@/lib/dwi/capture-draft-saver";

export type CohortPart = { id: string; label: string; /** why it can't be loaded */ held?: string };

export function BatchPanel({
    workOrderId,
    stepId,
    cohortParts,
    cohortTruncated = false,
    onChange,
}: {
    workOrderId: string;
    stepId: string;
    /** Parts currently at this (WO, Step). The operator picks which of these
     *  go into THIS load — a step can run several batches (furnace/wash loads)
     *  as long as their membership is disjoint. */
    cohortParts: CohortPart[];
    /** True when the cohort query hit its page cap and may be incomplete —
     *  starting a load on a partial cohort would be wrong, so we block it. */
    cohortTruncated?: boolean;
    onChange?: () => void;
}) {
    const { data: batchesData, isLoading } = useBatchesForWoStep(workOrderId, stepId);
    const createBatch = useCreateBatchExecution();
    const sealBatch = useSealBatchExecution();
    const completeBatch = useCompleteBatchExecution();
    const [sealingId, setSealingId] = useState<string | null>(null);
    const [completingId, setCompletingId] = useState<string | null>(null);
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    // The step's seal point, if one is authored: confirming it seals the load, so
    // there's no Seal button.
    const { data: stepSubsteps } = useSubsteps(stepId ? { step: stepId } : undefined);
    const sealPoint = (stepSubsteps?.results ?? []).find(
        (s: Substep) => s.scope === "batch" && (s as { seals_load?: boolean }).seals_load);

    const batches = batchesData?.results ?? [];
    const loadingBatches = batches.filter((b) => !b.sealed_at);
    const runningBatches = batches.filter((b) => b.sealed_at && !b.completed_at);
    const completedBatches = batches.filter((b) => b.completed_at);
    // Loading or running: still holding its parts.
    const openBatches = [...loadingBatches, ...runningBatches];

    // Disjoint membership: a part in a load not yet completed — loading or running —
    // can't join another, so the picker only offers parts not in one. Parts in a
    // COMPLETED load ARE still offered (a reworked part can re-batch on a later
    // visit) but get tagged below so they don't read-batched.
    const openBatchedIds = new Set(
        openBatches.flatMap((b) => (b.parts ?? []).map((p) => String(p))),
    );
    const sealedBatchedIds = new Set(
        completedBatches.flatMap((b) => (b.parts ?? []).map((p) => String(p))),
    );
    const availableParts = cohortParts.filter((p) => !openBatchedIds.has(p.id));
    // "Fresh" = in no batch at all. Coverage + select-all key off these so a
    // part sitting in a sealed load isn't counted/treated-batched.
    const freshParts = availableParts.filter((p) => !sealedBatchedIds.has(p.id) && !p.held);

    const toggle = (id: string) =>
        setSelectedIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });

    // Select-all targets the fresh (never-batched) parts — the common "start a
    // load with everything left" — so it doesn't sweep already-sealed units
    // back into a new load. A redo of a sealed part stays a deliberate click.
    const allFreshSelected =
        freshParts.length > 0 && freshParts.every((p) => selectedIds.has(p.id));
    const toggleAll = () =>
        setSelectedIds(
            allFreshSelected ? new Set() : new Set(freshParts.map((p) => p.id)),
        );

    const handleStart = () => {
        const parts = availableParts.filter((p) => !p.held).map((p) => p.id).filter((id) => selectedIds.has(id));
        if (parts.length === 0) {
            toast.error("Select at least one part for this load.");
            return;
        }
        createBatch.mutate(
            { work_order: workOrderId, step: stepId, parts },
            {
                onSuccess: () => {
                    setSelectedIds(new Set());
                    onChange?.();
                },
                onError: (err: unknown) => {
                    toast.error(apiErrorMessage(err) ?? "Could not start batch.");
                },
            },
        );
    };

    const handleSeal = (id: string) => {
        setSealingId(id);
        sealBatch.mutate(
            { id },
            {
                onSettled: () => setSealingId(null),
                onSuccess: () => onChange?.(),
                onError: (err: unknown) => {
                    const detail = (err as {
                        response?: { data?: { problems?: string[]; detail?: string } };
                    })?.response?.data;
                    const msg = detail?.problems?.join("; ") ?? detail?.detail ?? "Seal failed.";
                    toast.error(msg);
                },
            },
        );
    };

    const handleComplete = (id: string) => {
        setCompletingId(id);
        completeBatch.mutate(
            { id },
            {
                onSettled: () => setCompletingId(null),
                onSuccess: () => onChange?.(),
                onError: (err: unknown) => {
                    const detail = (err as {
                        response?: { data?: { problems?: string[]; detail?: string } };
                    })?.response?.data;
                    toast.error("The load isn't complete yet", {
                        description: detail?.problems?.join("; ") ?? detail?.detail ?? "Try again.",
                    });
                },
            },
        );
    };

    const totalAtStep = cohortParts.length;
    const unbatched = freshParts.length;            // never in any batch, and loadable
    // In an open OR sealed load — counted, not derived: a held unit is neither batched
    // nor loadable, and deriving it read "2/2 in a load" with one loaded.
    const batchedAtStep = cohortParts.filter(
        (p) => openBatchedIds.has(p.id) || sealedBatchedIds.has(p.id)).length;
    const heldAtStep = cohortParts.filter((p) => p.held).length;

    return (
        <div className="rounded-lg border bg-card">
            <div className="border-b px-4 py-2">
                <div className="flex items-center gap-2">
                    <Package className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Batch step</span>
                    <span className="ml-auto text-xs text-muted-foreground">
                        {loadingBatches.length} loading · {runningBatches.length} running · {completedBatches.length} completed
                    </span>
                </div>
                {/* 3b — up-front batch-gating context: this step moves by load,
                    not part-by-part, and each completed load advances on its own. */}
                <p className="mt-1 text-xs text-muted-foreground">
                    Parts advance by <span className="font-medium">load</span>. Load the units
                    going through this op together and do the loading checks, then seal: the
                    machine runs and you can leave it. Come back to finish the load's checks
                    and complete it. Each completed load moves on independently.
                </p>
                {totalAtStep > 0 && (
                    <p className="mt-1 text-xs">
                        <span className="font-medium">{batchedAtStep}</span>/{totalAtStep} parts in a
                        load
                        {unbatched > 0 && (
                            <span className="text-muted-foreground">
                                {" "}· {unbatched} not yet batched
                            </span>
                        )}
                        {heldAtStep > 0 && (
                            <span className="text-muted-foreground">
                                {" "}· {heldAtStep} held
                            </span>
                        )}
                    </p>
                )}
            </div>

            <div className="space-y-2 p-3">
                {isLoading ? (
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Loading batches…
                    </div>
                ) : (
                    <>
                        {batches.length === 0 && (
                            <p className="text-xs text-muted-foreground">
                                No batches yet for this WO/step.
                            </p>
                        )}
                        {loadingBatches.map((b) => (
                            <div key={b.id} className="rounded border bg-background">
                                <div className="flex items-center gap-3 px-3 py-2 text-sm">
                                    <Badge variant="secondary" className="text-[10px]">Loading</Badge>
                                    <div className="flex-1 text-xs">
                                        <div className="font-mono">{b.id.slice(0, 8)}…</div>
                                        <div className="text-muted-foreground">
                                            {(b.parts ?? []).length} part{(b.parts ?? []).length === 1 ? "" : "s"} · started {new Date(b.started_at).toLocaleString()}
                                        </div>
                                    </div>
                                    {sealPoint ? (
                                        <span className="max-w-[12rem] text-right text-[11px] text-muted-foreground">
                                            Confirming “{sealPoint.title}” seals the load.
                                        </span>
                                    ) : (
                                        <Button
                                            size="sm"
                                            variant="default"
                                            disabled={sealingId === b.id}
                                            onClick={() => handleSeal(b.id)}
                                        >
                                            {sealingId === b.id ? (
                                                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                                            ) : (
                                                <Lock className="mr-1 h-3 w-3" />
                                            )}
                                            Seal load
                                        </Button>
                                    )}
                                </div>
                                <BatchCaptureSection
                                    batchId={b.id}
                                    stepId={stepId}
                                    phase="load"
                                    onCaptured={onChange}
                                />
                            </div>
                        ))}
                        {runningBatches.map((b) => (
                            <div key={b.id} className="rounded border bg-background">
                                <div className="flex items-center gap-3 px-3 py-2 text-sm">
                                    <Badge variant="outline" className="border-blue-500 text-[10px] text-blue-700 dark:text-blue-400">
                                        <Lock className="mr-1 h-3 w-3" /> Running
                                    </Badge>
                                    <div className="flex-1 text-xs">
                                        <div className="font-mono">{b.id.slice(0, 8)}…</div>
                                        <div className="text-muted-foreground">
                                            {(b.parts ?? []).length} part{(b.parts ?? []).length === 1 ? "" : "s"} · sealed{" "}
                                            {b.sealed_at ? new Date(b.sealed_at).toLocaleString() : ""}
                                        </div>
                                    </div>
                                    <Button
                                        size="sm"
                                        variant="default"
                                        disabled={completingId === b.id}
                                        onClick={() => handleComplete(b.id)}
                                    >
                                        {completingId === b.id ? (
                                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                                        ) : (
                                            <CheckCircle2 className="mr-1 h-3 w-3" />
                                        )}
                                        Complete load
                                    </Button>
                                </div>
                                <BatchCaptureSection
                                    batchId={b.id}
                                    stepId={stepId}
                                    phase="completion"
                                    onCaptured={onChange}
                                />
                            </div>
                        ))}
                        {completedBatches.map((b) => (
                            <div
                                key={b.id}
                                className="flex items-center gap-3 rounded border bg-background/60 px-3 py-2 text-sm opacity-70"
                            >
                                <Badge variant="outline" className="text-[10px]">
                                    <CheckCircle2 className="mr-1 h-3 w-3" /> Completed
                                </Badge>
                                <div className="flex-1 text-xs">
                                    <div className="font-mono">{b.id.slice(0, 8)}…</div>
                                    <div className="text-muted-foreground">
                                        {(b.parts ?? []).length} part{(b.parts ?? []).length === 1 ? "" : "s"} · completed{" "}
                                        {b.completed_at ? new Date(b.completed_at).toLocaleString() : ""}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </>
                )}

                {/* Start a new load — operator picks the units for THIS batch. */}
                <div className="space-y-2 rounded border border-dashed p-3">
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-medium">
                            Start a load — select its units
                        </span>
                        {freshParts.length > 0 && (
                            <button
                                type="button"
                                className="text-[11px] text-muted-foreground underline-offset-2 hover:underline"
                                onClick={toggleAll}
                            >
                                {allFreshSelected ? "Clear" : "Select all"}
                            </button>
                        )}
                    </div>

                    {cohortTruncated && (
                        <p className="rounded bg-destructive/10 px-2 py-1 text-[11px] text-destructive">
                            This step has more parts than were loaded — the list may be
                            incomplete. Starting a load now could miss units. Narrow the
                            view or page before batching.
                        </p>
                    )}

                    {availableParts.length === 0 ? (
                        <p className="text-[11px] text-muted-foreground">
                            No un-batched parts available at this step.
                        </p>
                    ) : (
                        <div className="max-h-40 space-y-1 overflow-auto">
                            {availableParts.map((p) => {
                                const inSealed = sealedBatchedIds.has(p.id);
                                return (
                                    <label
                                        key={p.id}
                                        className={"flex items-center gap-2 rounded px-1 py-0.5 text-xs "
                                            + (p.held ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:bg-muted/50")}
                                    >
                                        <input
                                            type="checkbox"
                                            className="h-3.5 w-3.5"
                                            checked={!p.held && selectedIds.has(p.id)}
                                            disabled={Boolean(p.held)}
                                            aria-label={p.held ? `${p.label} — ${p.held}` : p.label}
                                            onChange={() => toggle(p.id)}
                                        />
                                        <span className={"font-mono" + (inSealed ? " text-muted-foreground" : "")}>
                                            {p.label}
                                        </span>
                                        {p.held && (
                                            <span className="text-[10px] text-muted-foreground">{p.held}</span>
                                        )}
                                        {inSealed && (
                                            <Badge variant="outline" className="text-[9px] text-muted-foreground">
                                                in a completed load
                                            </Badge>
                                        )}
                                    </label>
                                );
                            })}
                        </div>
                    )}

                    <Button
                        size="sm"
                        variant="outline"
                        className="w-full justify-center"
                        disabled={
                            createBatch.isPending ||
                            cohortTruncated ||
                            selectedIds.size === 0
                        }
                        onClick={handleStart}
                    >
                        {createBatch.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                        Start load ({selectedIds.size} selected)
                    </Button>
                </div>
            </div>
        </div>
    );
}

const EMPTY_DOC = { type: "doc", content: [] } as const;

const batchCaptureStateOptions = (batchId: string) =>
    queryOptions({
        queryKey: ["batch-capture-state", batchId],
        queryFn: () => api.api_BatchExecutions_capture_state_retrieve({ params: { id: batchId } }),
    });

/**
 * Once-per-lot capture surface for one phase of a load. Renders the step's
 * BATCH-scope substeps of that phase — up to the seal point while loading, the
 * rest once it's running — with the same operator view the per-part runtime
 * uses, but submits each to the batch (`{ batch_execution, captures }`)
 * rather than a per-part StepExecution. A phase's captures stay editable until
 * it ends (seal, then Complete); re-submitting a substep upserts its
 * completion server-side.
 */
function BatchCaptureSection({
    batchId,
    stepId,
    phase,
    onCaptured,
}: {
    batchId: string;
    stepId: string;
    phase: "load" | "completion";
    onCaptured?: () => void;
}) {
    const { data: substepsData, isLoading } = useSubsteps(stepId ? { step: stepId } : undefined);
    const submit = useSubmitSubstep();
    const qc = useQueryClient();
    // Signature blocks are signed where they sit; this prompt is only the retry path.
    const signaturePrompt = useSignaturePrompt();
    const [responsesBySubstep, setResponsesBySubstep] = useState<
        Record<string, OperatorResponses>
    >({});
    const [capturedIds, setCapturedIds] = useState<Set<string>>(new Set());
    const [submittingId, setSubmittingId] = useState<string | null>(null);
    // The substep last typed into: the one the autosave has queued.
    const [editingId, setEditingId] = useState<string | null>(null);

    // What the load already holds — confirmed captures with any draft over them —
    // so walking away from a half-entered load and coming back loses nothing.
    const { data: storedState } = useQuery(batchCaptureStateOptions(batchId));
    const { data: completions } = useQuery(batchCompletionsOptions([batchId]));
    const [hydrated, setHydrated] = useState(false);
    const draftWarned = useRef(false);
    const { markSaved } = useDraftAutosave({
        current: editingId
            ? {
                kind: "batch",
                executionId: batchId,
                substepId: editingId,
                responses: (responsesBySubstep[editingId] ?? {}) as Record<string, unknown>,
            }
            : null,
        ready: hydrated,
        onRefused: (detail) => toast.error("The load's entries aren't being saved", { description: detail }),
        onSignedOut: () => toast.error("Your last load entries weren't saved", {
            description: "You were signed out before they reached the server. " +
                "Sign in and re-enter them on the load.",
            duration: Infinity,
        }),
        onFailed: () => {
            if (draftWarned.current) return;
            draftWarned.current = true;
            toast.warning("Couldn't save the load's progress", {
                description: "It's still on this screen, and Confirm for batch records it.",
            });
        },
    });
    useEffect(() => {
        if (hydrated || !storedState || !completions) return;
        const state = storedState as Record<string, Record<string, unknown>>;
        markSaved(batchId, state);
        setResponsesBySubstep((prev) => (Object.keys(prev).length ? prev : state));
        setCapturedIds((prev) => prev.size ? prev : new Set(
            (completions.results ?? [])
                .filter((c) => !c.is_voided)
                .map((c) => String(c.substep)),
        ));
        setHydrated(true);
    }, [hydrated, storedState, completions, batchId, markSaved]);

    // The step's batch substeps in order; the one flagged "Seals the load" ends the
    // load phase (with none, every batch substep is loading and completion is bare).
    const allBatch = (substepsData?.results ?? [])
        .filter((s: Substep) => s.scope === "batch")
        .sort((a: Substep, b: Substep) => (a.order ?? 0) - (b.order ?? 0));
    const sealAt = allBatch.findIndex((s: Substep) => (s as { seals_load?: boolean }).seals_load);
    const batchSubsteps = sealAt === -1
        ? (phase === "load" ? allBatch : [])
        : (phase === "load" ? allBatch.slice(0, sealAt + 1) : allBatch.slice(sealAt + 1));

    if (isLoading || batchSubsteps.length === 0) return null;

    const setResponse = (substepId: string, nodeId: string, value: unknown) => {
        setEditingId(substepId);
        setResponsesBySubstep((prev) => ({
            ...prev,
            [substepId]: { ...(prev[substepId] ?? {}), [nodeId]: value },
        }));
    };

    const handleConfirm = async (substep: Substep) => {
        const body = substep.body_blocks ?? EMPTY_DOC;
        const responses = responsesBySubstep[substep.id] ?? {};
        const missing = findMissingRequired(body, responses);
        if (missing.length > 0) {
            toast.error("Complete the required fields before confirming for the batch.");
            return;
        }
        const captures = buildCaptures(body, responses);
        // Its Signature + password blocks were signed where they sit; the server checks
        // them and asks for no second, substep-level signature.
        setSubmittingId(substep.id);
        try {
            const refused = await submitSignedSubstep(substep, undefined, signaturePrompt.request,
                (fields) => submit.mutateAsync({
                    id: substep.id,
                    data: { batch_execution: batchId, captures, ...fields },
                }));
            if (refused === null) {
                // Committed: the server holds these now, so the autosave mustn't send
                // them back as a draft.
                markSaved(batchId, { [substep.id]: responses as Record<string, unknown> });
                // The seal point sealed the load: it moves from Loading to Running.
                if ((substep as { seals_load?: boolean }).seals_load) void invalidateBatches(qc);
                setCapturedIds((prev) => new Set(prev).add(substep.id));
                toast.success((substep as { seals_load?: boolean }).seals_load
                    ? `Captured "${substep.title}": the load is sealed and running.`
                    : `Captured "${substep.title}" for the batch.`);
                onCaptured?.();
            } else {
                toast.error(`"${substep.title}" not captured: ${refused}`);
            }
        } finally {
            setSubmittingId(null);
        }
    };

    return (
        <div className="space-y-2 border-t px-3 py-2">
            {signaturePrompt.dialog}
            <p className="text-xs font-medium text-muted-foreground">
                {phase === "load"
                    ? "Loading checks — captured once for the whole load"
                    : "Completion checks — once the run is done, before Complete load"}
            </p>
            {batchSubsteps.map((s: Substep) => {
                const captured = capturedIds.has(s.id);
                const busy = submittingId === s.id;
                return (
                    <div key={s.id} className="rounded border bg-card p-2">
                        <div className="mb-1 flex items-center gap-2">
                            <span className="text-sm font-medium">{s.title}</span>
                            {!s.is_optional && (
                                <Badge variant="secondary" className="text-[10px]">Required</Badge>
                            )}
                            {captured && (
                                <Badge variant="outline" className="ml-auto text-[10px]">
                                    <CheckCircle2 className="mr-1 h-3 w-3" /> Captured
                                </Badge>
                            )}
                        </div>
                        <OperatorResponseContext.Provider
                            value={{
                                responses: responsesBySubstep[s.id] ?? {},
                                setResponse: (nodeId, value) => setResponse(s.id, nodeId, value),
                            }}
                        >
                            {/* A signature block inside a batch substep signs once for
                                the whole load, so it needs the load — not a part. */}
                            <PartContext.Provider
                                value={{ batch_execution_id: batchId, substep_id: s.id }}
                            >
                                <SubstepOperatorView
                                    body={s.body_blocks ?? EMPTY_DOC}
                                />
                            </PartContext.Provider>
                        </OperatorResponseContext.Provider>
                        <Button
                            size="sm"
                            className="mt-2"
                            disabled={busy}
                            onClick={() => handleConfirm(s)}
                        >
                            {busy && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                            {captured ? "Update batch capture" : "Confirm for batch"}
                        </Button>
                    </div>
                );
            })}
        </div>
    );
}
