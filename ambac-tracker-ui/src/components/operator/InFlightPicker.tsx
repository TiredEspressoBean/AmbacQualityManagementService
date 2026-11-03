/**
 * The work someone has open — part visits and unsealed loads — to pick one up again.
 * One component in two places: Operator Home's Resume (when more than one is open)
 * and a work order's Continue work (narrowed to that order). Picking one opens the
 * runtime with no position, so it continues at the first substep not yet complete.
 */
import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { queryOptions, useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Loader2, Package } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";

export type InFlightItem = components["schemas"]["InFlightItem"];

export const inFlightOptions = (workOrderId?: string) =>
    queryOptions({
        queryKey: ["step-executions", "in-flight", workOrderId ?? null],
        queryFn: () => api.api_StepExecutions_in_flight_list(
            workOrderId ? { queries: { work_order: workOrderId } } : undefined,
        ) as Promise<InFlightItem[]>,
    });

/** Open the runtime on an in-flight item: the visit itself, or a load from one of its parts. */
export function useOpenInFlight() {
    const navigate = useNavigate();
    return (item: InFlightItem) => navigate({
        to: "/operator/steps/$stepId/substeps",
        params: { stepId: item.step_id },
        search: {
            // part is null on receiving / outside-process return runs; the runtime
            // resolves those from the execution alone.
            part: item.resume_part_id ?? undefined,
            // A batch step's panel needs the work order.
            workOrder: item.work_order_id ?? undefined,
            execution: item.resume_execution_id ?? undefined,
        },
    });
}

function since(item: InFlightItem) {
    if (item.started_at) return `started ${formatDistanceToNow(new Date(item.started_at))} ago`;
    if (item.entered_at) return `waiting ${formatDistanceToNow(new Date(item.entered_at))}`;
    return "";
}

export function InFlightPicker({ open, onOpenChange, workOrderId, title = "Pick up where you left off" }: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    workOrderId?: string;
    title?: string;
}) {
    const { data, isLoading } = useQuery({ ...inFlightOptions(workOrderId), enabled: open });
    const openItem = useOpenInFlight();
    const items = data ?? [];

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>{title}</DialogTitle>
                    <DialogDescription>
                        Your open steps and loads{workOrderId ? " on this work order" : ""}, most
                        recently started first. Each opens at its first substep not yet done.
                    </DialogDescription>
                </DialogHeader>
                {isLoading ? (
                    <div className="flex justify-center py-6"><Loader2 className="h-5 w-5 animate-spin" /></div>
                ) : items.length === 0 ? (
                    <p className="py-4 text-sm text-muted-foreground">Nothing open.</p>
                ) : (
                    <ul className="max-h-[60vh] space-y-2 overflow-auto">
                        {items.map((item) => (
                            <li key={`${item.kind}:${item.id}`}>
                                <button
                                    type="button"
                                    disabled={!item.resume_execution_id}
                                    onClick={() => { onOpenChange(false); void openItem(item); }}
                                    className="flex w-full items-start justify-between gap-3 rounded-md border p-3 text-left hover:bg-accent disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    <div className="min-w-0">
                                        <div className="truncate font-medium">{item.step_name}</div>
                                        <div className="truncate font-mono text-xs text-muted-foreground">
                                            {item.kind === "load"
                                                ? <span className="inline-flex items-center gap-1"><Package className="h-3 w-3" /> Load · {item.part_count} part{item.part_count === 1 ? "" : "s"}</span>
                                                : item.part_erp_id ?? "—"}
                                            {item.work_order_erp_id ? ` · ${item.work_order_erp_id}` : ""}
                                        </div>
                                        <div className="text-xs text-muted-foreground">
                                            {item.kind === "load" ? "Open load"
                                                : item.status === "IN_PROGRESS" ? "Running" : "Assigned"}
                                            {since(item) ? ` · ${since(item)}` : ""}
                                        </div>
                                        {!item.resume_execution_id && (
                                            <div className="text-xs text-amber-700 dark:text-amber-400">
                                                None of this load's parts is still at the step.
                                            </div>
                                        )}
                                    </div>
                                    {item.substeps_total > 0 && (
                                        <Badge variant="secondary" className="shrink-0 font-normal">
                                            {item.substeps_done} of {item.substeps_total} done
                                        </Badge>
                                    )}
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
                <div className="flex justify-end">
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}

/** A work order's "Continue work": shown only when the user has something open on it —
 * back to the traveller after the wash, say — and opens the picker narrowed to it. */
export function ContinueWorkButton({ workOrderId }: { workOrderId: string }) {
    const { data } = useQuery(inFlightOptions(workOrderId));
    const [open, setOpen] = useState(false);
    if (!data?.length) return null;
    return (
        <>
            <Button variant="outline" onClick={() => setOpen(true)}>
                Continue work ({data.length})
            </Button>
            <InFlightPicker open={open} onOpenChange={setOpen} workOrderId={workOrderId}
                title="Continue work on this order" />
        </>
    );
}
