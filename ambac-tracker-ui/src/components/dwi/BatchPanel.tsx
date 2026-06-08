/**
 * Operator-runtime BatchPanel.
 *
 * Surfaces when the current Step has at least one BATCH-scope substep.
 * Lets an operator:
 *   - Start a BatchExecution that includes the cohort at (WO, Step)
 *   - See existing open / sealed batches for the same (WO, Step)
 *   - Seal an open batch
 *
 * Capturing the BATCH-scope substep data lives in a future iteration —
 * for now the panel exists to close the seal lifecycle so the lot
 * cohesion engine can fire advancement when batch-substep substeps
 * land via API.
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

export function BatchPanel({
    workOrderId,
    stepId,
    cohortPartIds,
    onChange,
}: {
    workOrderId: string;
    stepId: string;
    /** Part IDs currently at this (WO, Step). The "Start batch with cohort"
     *  action seeds this list onto the new BatchExecution. */
    cohortPartIds: string[];
    onChange?: () => void;
}) {
    const { data: batchesData, isLoading } = useBatchesForWoStep(workOrderId, stepId);
    const createBatch = useCreateBatchExecution();
    const sealBatch = useSealBatchExecution();
    const [sealingId, setSealingId] = useState<string | null>(null);

    const batches = batchesData?.results ?? [];
    const openBatches = batches.filter((b) => !b.sealed_at);
    const sealedBatches = batches.filter((b) => b.sealed_at);

    const handleStart = () => {
        if (cohortPartIds.length === 0) {
            toast.error("No cohort parts at this step.");
            return;
        }
        createBatch.mutate(
            {
                work_order: workOrderId,
                step: stepId,
                parts: cohortPartIds,
            },
            { onSuccess: () => onChange?.() },
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

    return (
        <div className="rounded-lg border bg-card">
            <div className="flex items-center gap-2 border-b px-4 py-2">
                <Package className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Batch operations at this step</span>
                <span className="ml-auto text-xs text-muted-foreground">
                    {openBatches.length} open · {sealedBatches.length} sealed
                </span>
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
                            <div
                                key={b.id}
                                className="flex items-center gap-3 rounded border bg-background px-3 py-2 text-sm"
                            >
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

                <Button
                    size="sm"
                    variant="outline"
                    className="w-full justify-center"
                    disabled={createBatch.isPending || cohortPartIds.length === 0}
                    onClick={handleStart}
                    title={
                        cohortPartIds.length === 0
                            ? "No parts at this WO/step."
                            : `Start a new batch with ${cohortPartIds.length} cohort part(s).`
                    }
                >
                    {createBatch.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                    Start batch with cohort ({cohortPartIds.length})
                </Button>
            </div>
        </div>
    );
}
