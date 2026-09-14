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
import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useReportActivity } from "@/hooks/useReportActivity";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

const csrfHeaders = () => ({ "X-CSRFToken": getCookie("csrftoken") ?? "" });

// Declared on the action now, so the summary shape comes from the client
// rather than being restated here.
type ReconcileSummary = Awaited<
    ReturnType<typeof api.api_SamplingDecisions_reconcile_create>
>;

const pendingDecisionsOptions = (workOrderId: string) =>
    queryOptions({
        queryKey: ["samplingDecisions", "pending-by-wo", workOrderId] as const,
        queryFn: () =>
            api.api_SamplingDecisions_list({
                queries: {
                    outcome: "pending",
                    // This related lookup is a declared filter now. It was
                    // being passed undeclared, and django-filter drops params
                    // it doesn't know -- so the panel was listing every
                    // PENDING decision in the tenant, not this work order's.
                    step_execution__part__work_order: workOrderId,
                },
            }),
        enabled: !!workOrderId,
        staleTime: 15_000,
    });

function usePendingDecisionsForWorkOrder(workOrderId: string) {
    return useQuery(pendingDecisionsOptions(workOrderId));
}

function useReconcilePendingDecisions() {
    const qc = useQueryClient();
    return useMutation<
        ReconcileSummary,
        unknown,
        { work_order_id: string; step_id?: string }
    >({
        mutationFn: (data) =>
            api.api_SamplingDecisions_reconcile_create(data, {
                headers: csrfHeaders(),
            }),
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
    onActivity,
}: {
    workOrderId: string;
    onActivity?: (active: boolean) => void;
}) {
    const { data, isLoading } = usePendingDecisionsForWorkOrder(workOrderId);
    const reconcile = useReconcilePendingDecisions();

    const pending = data?.results ?? [];
    useReportActivity(pending.length > 0, onActivity);

    if (isLoading) {
        return (
            <div className="flex items-center gap-2 rounded border bg-card p-4 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading PENDING decisions…
            </div>
        );
    }

    // Self-hide when there's nothing pending (like the FPI / OSP panels), rather
    // than occupying the Control page with a persistent "nothing here" card. The
    // "lot is clear" reassurance isn't worth a permanent card on a busy surface.
    if (pending.length === 0) {
        return null;
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
