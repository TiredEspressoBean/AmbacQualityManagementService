/**
 * The work someone has open — part visits and unsealed loads — to pick one up again.
 * One component in two places: Operator Home's Resume (when more than one is open)
 * and a work order's Continue work (narrowed to that order). Picking one opens the
 * runtime with no position, so it continues at the first substep not yet complete.
 *
 * A supervisor (`reassign_stepexecution`: the leads, the production manager, the QA
 * manager) can switch to everyone's work, narrow it to work whose holder is off the
 * clock, and take a step over or hand it to a named operator, with a reason. Whoever
 * ends up holding it must be trained for it; the server says so when they aren't.
 */
import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Loader2, Package } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useAuthUser } from "@/hooks/useAuthUser";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";
import { getCookie } from "@/lib/utils";

export type InFlightItem = components["schemas"]["InFlightItem"];

type Scope = { workOrderId?: string; everyone?: boolean; offClock?: boolean };

export const inFlightOptions = (workOrderId?: string, scope: Omit<Scope, "workOrderId"> = {}) =>
    queryOptions({
        queryKey: ["step-executions", "in-flight", workOrderId ?? null,
            Boolean(scope.everyone), Boolean(scope.offClock)],
        queryFn: () => api.api_StepExecutions_in_flight_list({
            queries: {
                ...(workOrderId ? { work_order: workOrderId } : {}),
                ...(scope.everyone ? { everyone: true } : {}),
                ...(scope.offClock ? { off_clock: true } : {}),
            },
        }) as Promise<InFlightItem[]>,
    });

export type HandOffCandidate = components["schemas"]["HandOffCandidate"];

/** Who a step can be handed to: staff who record substeps, trained first. */
const handOffCandidatesOptions = (executionId: string) =>
    queryOptions({
        queryKey: ["step-executions", "hand-off-candidates", executionId],
        queryFn: () => api.api_StepExecutions_hand_off_candidates_list({ params: { id: executionId } }) as Promise<HandOffCandidate[]>,
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
    // A running load: what matters is how long the machine has had it.
    if (item.sealed_at) return `sealed ${formatDistanceToNow(new Date(item.sealed_at))} ago`;
    if (item.started_at) return `started ${formatDistanceToNow(new Date(item.started_at))} ago`;
    if (item.entered_at) return `waiting ${formatDistanceToNow(new Date(item.entered_at))}`;
    return "";
}

const isSupervisor = (perms: { has: (perm: string) => boolean }) => perms.has("reassign_stepexecution");

export function InFlightPicker({ open, onOpenChange, workOrderId, title = "Pick up where you left off",
    initialEveryone = false, initialOffClock = false }: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    workOrderId?: string;
    title?: string;
    /** Open on everyone's work (a supervisor with nothing of their own here). */
    initialEveryone?: boolean;
    /** Open narrowed to work whose holder is off the clock. */
    initialOffClock?: boolean;
}) {
    const perms = usePermissionSet();
    const supervisor = isSupervisor(perms);
    const { data: me } = useAuthUser();
    const [everyone, setEveryone] = useState(initialEveryone);
    const [offClock, setOffClock] = useState(initialOffClock);
    const [moving, setMoving] = useState<{ item: InFlightItem; mode: "take" | "hand" } | null>(null);
    const { data, isLoading } = useQuery({
        ...inFlightOptions(workOrderId, { everyone: supervisor && everyone, offClock: supervisor && everyone && offClock }),
        enabled: open,
    });
    const openItem = useOpenInFlight();
    const items = data ?? [];
    const mine = (item: InFlightItem) => item.holder_id === me?.pk;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>{title}</DialogTitle>
                    <DialogDescription>
                        {everyone ? "Everyone's" : "Your"} open steps and loads
                        {workOrderId ? " on this work order" : ""}, most recently started
                        first. Each opens at its first substep not yet done.
                    </DialogDescription>
                </DialogHeader>
                {supervisor && (
                    <div className="flex flex-wrap items-center gap-2">
                        <Button size="sm" variant={everyone ? "outline" : "secondary"} onClick={() => setEveryone(false)}>
                            Mine
                        </Button>
                        <Button size="sm" variant={everyone ? "secondary" : "outline"} onClick={() => setEveryone(true)}>
                            Everyone's
                        </Button>
                        {everyone && (
                            <Button size="sm" variant={offClock ? "secondary" : "outline"} onClick={() => setOffClock((v) => !v)}>
                                Off the clock only
                            </Button>
                        )}
                    </div>
                )}
                {isLoading ? (
                    <div className="flex justify-center py-6"><Loader2 className="h-5 w-5 animate-spin" /></div>
                ) : items.length === 0 ? (
                    <p className="py-4 text-sm text-muted-foreground">Nothing open.</p>
                ) : (
                    <ul className="max-h-[60vh] space-y-2 overflow-auto">
                        {items.map((item) => (
                            <li key={`${item.kind}:${item.id}`} className="rounded-md border">
                                <button
                                    type="button"
                                    // Someone else's step is theirs until it's taken over.
                                    disabled={!item.resume_execution_id || !mine(item)}
                                    onClick={() => { onOpenChange(false); void openItem(item); }}
                                    className="flex w-full items-start justify-between gap-3 p-3 text-left hover:bg-accent disabled:cursor-default disabled:hover:bg-transparent"
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
                                            {item.kind === "load"
                                                ? (item.status === "RUNNING" ? "Running" : "Loading")
                                                : item.status === "IN_PROGRESS" ? "Running" : "Assigned"}
                                            {since(item) ? ` · ${since(item)}` : ""}
                                            {!mine(item) && item.holder_name ? ` · ${item.holder_name}` : ""}
                                        </div>
                                        {!item.resume_execution_id && (
                                            <div className="text-xs text-amber-700 dark:text-amber-400">
                                                None of this load's parts is still at the step.
                                            </div>
                                        )}
                                    </div>
                                    <div className="flex shrink-0 flex-col items-end gap-1">
                                        {item.substeps_total > 0 && (
                                            <Badge variant="secondary" className="font-normal">
                                                {item.substeps_done} of {item.substeps_total} done
                                            </Badge>
                                        )}
                                        {everyone && item.holder_off_clock && (
                                            <Badge variant="outline" className="border-amber-500 font-normal text-amber-700 dark:text-amber-400">
                                                Off the clock
                                            </Badge>
                                        )}
                                    </div>
                                </button>
                                {/* A load is shared work, not one person's step: nothing to take over. */}
                                {supervisor && item.kind === "part" && (
                                    <div className="flex gap-2 border-t px-3 py-2">
                                        {!mine(item) && (
                                            <Button size="sm" variant="outline" onClick={() => setMoving({ item, mode: "take" })}>
                                                Take over
                                            </Button>
                                        )}
                                        <Button size="sm" variant="outline" onClick={() => setMoving({ item, mode: "hand" })}>
                                            Hand off…
                                        </Button>
                                    </div>
                                )}
                            </li>
                        ))}
                    </ul>
                )}
                <div className="flex justify-end">
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
                </div>
                {moving && (
                    <ReassignDialog
                        item={moving.item}
                        mode={moving.mode}
                        meId={me?.pk}
                        onClose={() => setMoving(null)}
                        onTaken={(item) => { setMoving(null); onOpenChange(false); void openItem(item); }}
                    />
                )}
            </DialogContent>
        </Dialog>
    );
}

/** Take a step over (to yourself) or hand it to a named operator, with a reason. */
function ReassignDialog({ item, mode, meId, onClose, onTaken }: {
    item: InFlightItem;
    mode: "take" | "hand";
    meId: number | undefined;
    onClose: () => void;
    onTaken: (item: InFlightItem) => void;
}) {
    const qc = useQueryClient();
    const [reason, setReason] = useState("");
    const [to, setTo] = useState<string>("");
    const { data: people } = useQuery({ ...handOffCandidatesOptions(item.id), enabled: mode === "hand" });
    const target = mode === "take" ? meId : Number(to) || undefined;
    const reassign = useMutation({
        mutationFn: () => api.api_StepExecutions_reassign_create(
            { to: target as number, reason },
            {
                params: { id: item.id },
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
                suppressErrorToast: true,
            },
        ),
        // The dialog's own toast says why; no second, generic one.
        meta: { suppressGlobalError: true },
        onSuccess: () => {
            void qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "step-executions" });
            if (mode === "take") {
                toast.success(`${item.step_name} is yours now`);
                onTaken(item);
            } else {
                toast.success(`${item.step_name} handed off`);
                onClose();
            }
        },
        onError: (err: unknown) => {
            const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
            toast.error("The step didn't change hands", { description: detail ?? "Try again." });
        },
    });

    return (
        <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>{mode === "take" ? "Take over this step" : "Hand off this step"}</DialogTitle>
                    <DialogDescription>
                        {item.step_name} · {item.part_erp_id ?? "—"}
                        {item.holder_name ? `, now ${item.holder_name}'s` : ""}. It keeps its
                        progress: {mode === "take" ? "you continue" : "they continue"} where it was left.
                    </DialogDescription>
                </DialogHeader>
                {mode === "hand" && (
                    <div className="space-y-1.5">
                        <Label>Hand to</Label>
                        <Select value={to} onValueChange={(v) => v && setTo(v)}>
                            <SelectTrigger><SelectValue placeholder="Pick an operator" /></SelectTrigger>
                            <SelectContent>
                                {(people ?? []).map((c) => (
                                    <SelectItem key={c.user_id} value={String(c.user_id)}>
                                        {c.name}
                                        <span className="ml-2 text-xs text-muted-foreground">
                                            {c.trained ? "trained" : "not trained for this step"}
                                            {c.at_station ? " · at this station" : ""}
                                        </span>
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                )}
                <div className="space-y-1.5">
                    <Label htmlFor="reassign-reason">Why</Label>
                    <Textarea id="reassign-reason" value={reason} onChange={(e) => setReason(e.target.value)}
                        placeholder={mode === "take" ? "e.g. Went home sick; finishing the lot" : "e.g. Moved to the bench; Sam finishes it"} />
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={onClose}>Cancel</Button>
                    <Button disabled={!reason.trim() || !target || reassign.isPending} onClick={() => reassign.mutate()}>
                        {reassign.isPending && <Loader2 className="mr-1 h-4 w-4 animate-spin" />}
                        {mode === "take" ? "Take over" : "Hand off"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

/** A work order's "Continue work": shown only when there is something open on it to
 * continue — your own, or, for a supervisor, anyone's — and opens the picker narrowed
 * to it (back to the traveller after the wash, say). */
export function ContinueWorkButton({ workOrderId }: { workOrderId: string }) {
    const supervisor = isSupervisor(usePermissionSet());
    const { data } = useQuery(inFlightOptions(workOrderId));
    const { data: anyone } = useQuery({ ...inFlightOptions(workOrderId, { everyone: true }), enabled: supervisor });
    const [open, setOpen] = useState(false);
    const count = data?.length ?? 0;
    if (!count && !(supervisor && anyone?.length)) return null;
    return (
        <>
            <Button variant="outline" onClick={() => setOpen(true)}>
                Continue work{count ? ` (${count})` : ""}
            </Button>
            <InFlightPicker open={open} onOpenChange={setOpen} workOrderId={workOrderId}
                title="Continue work on this order" initialEveryone={supervisor && !count} />
        </>
    );
}

/** A supervisor's way in to everyone's work in progress from their home page:
 *  how much is open across the plant and how much is held by someone off the clock,
 *  each opening the picker on Everyone's. Renders nothing for anyone else. */
export function WorkInProgressCard() {
    const supervisor = isSupervisor(usePermissionSet());
    const { data } = useQuery({ ...inFlightOptions(undefined, { everyone: true }), enabled: supervisor });
    const [open, setOpen] = useState<null | "all" | "off">(null);
    if (!supervisor) return null;
    const items = data ?? [];
    const off = items.filter((i) => i.holder_off_clock).length;
    return (
        <div className="rounded-lg border bg-card p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Work in progress</div>
            <p className="my-2 text-sm text-muted-foreground">
                Steps and loads open across the plant. Take one over, or hand it to someone.
            </p>
            <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={() => setOpen("all")}>
                    Work in progress ({items.length})
                </Button>
                <Button variant="outline" disabled={!off} onClick={() => setOpen("off")}
                    className={off ? "border-amber-500 text-amber-700 dark:text-amber-400" : ""}>
                    Off the clock ({off})
                </Button>
            </div>
            {open && (
                <InFlightPicker open onOpenChange={(o) => { if (!o) setOpen(null); }}
                    title="Work in progress" initialEveryone initialOffClock={open === "off"} />
            )}
        </div>
    );
}
