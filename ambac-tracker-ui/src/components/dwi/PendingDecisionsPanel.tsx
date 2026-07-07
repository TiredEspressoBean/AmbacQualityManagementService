/**
 * Supervisor PENDING reconciliation panel.
 *
 * Surfaces live PENDING SamplingDecisions for a WorkOrder so a
 * supervisor can resolve them before the WO advances past a terminal
 * step. PENDING comes from rules like LAST_N_PARTS / EXACT_COUNT that
 * can't decide at part entry — they need the cohort closed.
 *
 * The "Reconcile now" action calls the backend service that walks every
 * PENDING decision under the WO, re-evaluates with cohort-closed
 * context, and supersedes each row with a concrete outcome. The summary
 * is surfaced inline so the supervisor sees what flipped.
 *
 * This is Flow #11 of MES_BEHAVIOR_FLOWS.md.
 */

import { Loader2, AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

const csrfHeaders = () => ({ "X-CSRFToken": getCookie("csrftoken") ?? "" });

type SamplingDecisionRow = {
    id: string;
    step_execution: string;
    substep: string;
    outcome: "selected" | "deselected" | "pending";
    ruleset_version: number;
    decided_at: string;
    superseded_by: string | null;
};

type ReconcileSummary = {
    reconciled: number;
    now_selected: number;
    now_deselected: number;
    still_pending: number;
};

function usePendingDecisionsForWorkOrder(workOrderId: string) {
    return useQuery({
        queryKey: ["samplingDecisions", "pending-by-wo", workOrderId] as const,
        queryFn: () =>
            api.api_SamplingDecisions_list({
                queries: {
                    outcome: "pending",
                    // Backend filterset doesn't expose work_order directly;
                    // server-side filtering by step_execution__part__work_order
                    // is via the related lookup. The list endpoint also
                    // accepts arbitrary filters DRF resolves.
                    step_execution__part__work_order: workOrderId,
                } as never,
            }) as Promise<{ results?: SamplingDecisionRow[] }>,
        enabled: !!workOrderId,
        staleTime: 15_000,
    });
}

function useReconcilePendingDecisions() {
    const qc = useQueryClient();
    return useMutation<
        ReconcileSummary,
        unknown,
        { work_order_id: string; step_id?: string }
    >({
        mutationFn: (data) =>
            api.api_SamplingDecisions_reconcile_create(
                data as never,
                { headers: csrfHeaders() },
                // Schema gap: reconcile's summary response isn't declared on the
                // endpoint, so the generated type is the SamplingDecision shape.
            ) as unknown as Promise<ReconcileSummary>,
        onSuccess: () => {
            qc.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "samplingDecisions",
            });
            qc.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "parts",
            });
        },
        meta: {
            errorMessage: "Couldn't reconcile PENDING decisions",
        },
    });
}

export function PendingDecisionsPanel({
    workOrderId,
}: {
    workOrderId: string;
}) {
    const { data, isLoading } = usePendingDecisionsForWorkOrder(workOrderId);
    const reconcile = useReconcilePendingDecisions();

    const pending = data?.results ?? [];

    if (isLoading) {
        return (
            <div className="flex items-center gap-2 rounded border bg-card p-4 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading PENDING decisions…
            </div>
        );
    }

    if (pending.length === 0) {
        return (
            <div className="rounded border bg-card p-4 text-sm text-muted-foreground">
                No PENDING sampling decisions on this work order. The lot is
                clear of cohort-close reconciliation.
            </div>
        );
    }

    const handleReconcile = () => {
        reconcile.mutate(
            { work_order_id: workOrderId },
            {
                onSuccess: (summary) => {
                    toast.success("Reconciliation complete", {
                        description:
                            `${summary.reconciled} reconciled · ` +
                            `${summary.now_selected} now selected · ` +
                            `${summary.now_deselected} now deselected` +
                            (summary.still_pending > 0
                                ? ` · ${summary.still_pending} still PENDING (check rule config)`
                                : ""),
                    });
                },
            },
        );
    };

    return (
        <div className="rounded-lg border bg-card">
            <div className="flex items-center gap-2 border-b px-4 py-3">
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                <span className="text-sm font-medium">
                    PENDING sampling decisions
                </span>
                <Badge variant="outline" className="text-[10px]">
                    {pending.length} unresolved
                </Badge>
                <Button
                    size="sm"
                    onClick={handleReconcile}
                    disabled={reconcile.isPending}
                    className="ml-auto"
                >
                    {reconcile.isPending && <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />}
                    Reconcile now
                </Button>
            </div>
            <div className="space-y-1 p-3 text-xs">
                <p className="text-muted-foreground">
                    Rules like LAST_N_PARTS / EXACT_COUNT can't decide at
                    part entry — they need the cohort closed. The
                    terminal-step gate refuses to advance the lot until
                    these are resolved.
                </p>
                <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">
                        Show all {pending.length} PENDING row{pending.length === 1 ? "" : "s"}
                    </summary>
                    <ul className="mt-2 max-h-48 space-y-1 overflow-auto font-mono">
                        {pending.map((d) => (
                            <li key={d.id} className="flex items-center gap-2">
                                <span className="text-muted-foreground">{d.id.slice(0, 8)}…</span>
                                <span>substep {String(d.substep).slice(0, 8)}…</span>
                                <span className="text-muted-foreground">
                                    ruleset v{d.ruleset_version}
                                </span>
                            </li>
                        ))}
                    </ul>
                </details>
            </div>
        </div>
    );
}
