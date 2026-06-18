/**
 * Operator-runtime BatchPanel.
 *
 * Surfaces when the current Step has at least one BATCH-scope substep.
 * Lets an operator:
 *   - Start a BatchExecution for a chosen subset of units at (WO, Step) —
 *     a step can run several loads (furnace/wash/autoclave capacity), so the
 *     operator selects which units go into THIS load; membership is disjoint
 *   - See existing open / sealed batches for the same (WO, Step)
 *   - Capture the step's BATCH-scope substeps once for the lot (3a)
 *   - Seal an open batch
 *
 * BATCH-scope substeps are captured a single time per BatchExecution
 * (not per part): submit posts `{ batch_execution, captures }`, which the
 * backend binds to the batch via a SubstepCompletion. Once every required
 * BATCH substep has a completion, the batch can seal and the lot-cohesion
 * engine fires advancement.
 */

import { useState } from "react";
import { Loader2, Package, Lock, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
    useBatchesForWoStep,
    useCreateBatchExecution,
    useSealBatchExecution,
} from "@/hooks/useBatchExecutions";
import { useSubsteps, useSubmitSubstep, type Substep } from "@/hooks/useSubsteps";
import { SubstepOperatorView } from "@/components/dwi/SubstepOperatorView";
import {
    OperatorResponseContext,
    type OperatorResponses,
} from "@/components/dwi/shared/OperatorResponseContext";
import { buildCaptures, findMissingRequired } from "@/lib/dwi/build-captures";

export type CohortPart = { id: string; label: string };

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
    const [sealingId, setSealingId] = useState<string | null>(null);
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

    const batches = batchesData?.results ?? [];
    const openBatches = batches.filter((b) => !b.sealed_at);
    const sealedBatches = batches.filter((b) => b.sealed_at);

    // Disjoint membership: a part already in an OPEN batch can't join another.
    // Offer only the parts not yet committed to an open load.
    const batchedIds = new Set(
        openBatches.flatMap((b) => (b.parts ?? []).map((p) => String(p))),
    );
    const availableParts = cohortParts.filter((p) => !batchedIds.has(p.id));

    const toggle = (id: string) =>
        setSelectedIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });

    const allAvailableSelected =
        availableParts.length > 0 && availableParts.every((p) => selectedIds.has(p.id));
    const toggleAll = () =>
        setSelectedIds(
            allAvailableSelected ? new Set() : new Set(availableParts.map((p) => p.id)),
        );

    const handleStart = () => {
        const parts = availableParts.map((p) => p.id).filter((id) => selectedIds.has(id));
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
                    const detail = (err as {
                        response?: { data?: { detail?: string | string[] } };
                    })?.response?.data?.detail;
                    const msg = Array.isArray(detail) ? detail.join("; ") : detail;
                    toast.error(msg ?? "Could not start batch.");
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

    const totalAtStep = cohortParts.length;
    const unbatched = availableParts.length;
    const batchedAtStep = totalAtStep - unbatched;

    return (
        <div className="rounded-lg border bg-card">
            <div className="border-b px-4 py-2">
                <div className="flex items-center gap-2">
                    <Package className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Batch step</span>
                    <span className="ml-auto text-xs text-muted-foreground">
                        {openBatches.length} open · {sealedBatches.length} sealed
                    </span>
                </div>
                {/* 3b — up-front batch-gating context: this step moves by load,
                    not part-by-part, and each sealed load advances on its own. */}
                <p className="mt-1 text-xs text-muted-foreground">
                    Parts advance by <span className="font-medium">load</span> — group the units
                    going through this op together, capture once, then seal. Each sealed load
                    moves on independently.
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
                        {openBatches.length === 0 && sealedBatches.length === 0 && (
                            <p className="text-xs text-muted-foreground">
                                No batches yet for this WO/step.
                            </p>
                        )}
                        {openBatches.map((b) => (
                            <div key={b.id} className="rounded border bg-background">
                                <div className="flex items-center gap-3 px-3 py-2 text-sm">
                                    <Badge variant="secondary" className="text-[10px]">Open</Badge>
                                    <div className="flex-1 text-xs">
                                        <div className="font-mono">{b.id.slice(0, 8)}…</div>
                                        <div className="text-muted-foreground">
                                            {b.parts.length} parts · started {new Date(b.started_at).toLocaleString()}
                                        </div>
                                    </div>
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
                                        Seal batch
                                    </Button>
                                </div>
                                <BatchCaptureSection
                                    batchId={b.id}
                                    stepId={stepId}
                                    onCaptured={onChange}
                                />
                            </div>
                        ))}
                        {sealedBatches.map((b) => (
                            <div
                                key={b.id}
                                className="flex items-center gap-3 rounded border bg-background/60 px-3 py-2 text-sm opacity-70"
                            >
                                <Badge variant="outline" className="text-[10px]">
                                    <CheckCircle2 className="mr-1 h-3 w-3" /> Sealed
                                </Badge>
                                <div className="flex-1 text-xs">
                                    <div className="font-mono">{b.id.slice(0, 8)}…</div>
                                    <div className="text-muted-foreground">
                                        {b.parts.length} parts · sealed{" "}
                                        {b.sealed_at ? new Date(b.sealed_at).toLocaleString() : ""}
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
                        {availableParts.length > 0 && (
                            <button
                                type="button"
                                className="text-[11px] text-muted-foreground underline-offset-2 hover:underline"
                                onClick={toggleAll}
                            >
                                {allAvailableSelected ? "Clear" : "Select all"}
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
                            {availableParts.map((p) => (
                                <label
                                    key={p.id}
                                    className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 text-xs hover:bg-muted/50"
                                >
                                    <input
                                        type="checkbox"
                                        className="h-3.5 w-3.5"
                                        checked={selectedIds.has(p.id)}
                                        onChange={() => toggle(p.id)}
                                    />
                                    <span className="font-mono">{p.label}</span>
                                </label>
                            ))}
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

/**
 * Once-per-lot capture surface for an open batch. Renders the step's
 * BATCH-scope substeps with the same operator view the per-part runtime
 * uses, but submits each to the batch (`{ batch_execution, captures }`)
 * rather than a per-part StepExecution. Captures stay editable until the
 * batch is sealed (Decision #3); re-submitting a substep upserts its
 * completion server-side.
 */
function BatchCaptureSection({
    batchId,
    stepId,
    onCaptured,
}: {
    batchId: string;
    stepId: string;
    onCaptured?: () => void;
}) {
    const { data: substepsData, isLoading } = useSubsteps(stepId ? { step: stepId } : undefined);
    const submit = useSubmitSubstep();
    const [responsesBySubstep, setResponsesBySubstep] = useState<
        Record<string, OperatorResponses>
    >({});
    const [capturedIds, setCapturedIds] = useState<Set<string>>(new Set());
    const [submittingId, setSubmittingId] = useState<string | null>(null);

    const batchSubsteps = (substepsData?.results ?? []).filter(
        (s: Substep) => s.scope === "batch",
    );

    if (isLoading || batchSubsteps.length === 0) return null;

    const setResponse = (substepId: string, nodeId: string, value: unknown) =>
        setResponsesBySubstep((prev) => ({
            ...prev,
            [substepId]: { ...(prev[substepId] ?? {}), [nodeId]: value },
        }));

    const handleConfirm = async (substep: Substep) => {
        const body = (substep.body_blocks as unknown as object) ?? EMPTY_DOC;
        const responses = responsesBySubstep[substep.id] ?? {};
        const missing = findMissingRequired(body, responses);
        if (missing.length > 0) {
            toast.error("Complete the required fields before confirming for the batch.");
            return;
        }
        const captures = buildCaptures(body, responses);
        setSubmittingId(substep.id);
        try {
            await submit.mutateAsync({
                id: substep.id,
                data: { batch_execution: batchId, captures },
            });
            setCapturedIds((prev) => new Set(prev).add(substep.id));
            toast.success(`Captured "${substep.title}" for the batch.`);
            onCaptured?.();
        } catch {
            toast.error("Batch capture failed.");
        } finally {
            setSubmittingId(null);
        }
    };

    return (
        <div className="space-y-2 border-t px-3 py-2">
            <p className="text-xs font-medium text-muted-foreground">
                Batch substeps — captured once for the whole lot
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
                            <SubstepOperatorView
                                body={(s.body_blocks as unknown as object) ?? EMPTY_DOC}
                            />
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
