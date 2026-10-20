/**
 * Short-close: complete a work order with fewer built than planned. Every unit that
 * hasn't finished is scrapped or moved to another open work order on the same process
 * (it keeps its step there) — for the same customer or on no order; a customer's own
 * unit only to that customer's work. The server says which targets each unit may take. The order then reads Completed, short-closed, with the
 * reason. Same permission as Cancel (cancel_workorder); the server re-checks all of it.
 *
 * Two consequences are the closer's to decide, so neither is pre-selected: whether the
 * units it didn't build go back to the order line as demand still to plan, and whether
 * each work order receiving moved units has its quantity raised to match.
 */
import { useMemo, useState } from "react";
import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

/** Statuses at which a unit has ended (services/mes/parts._ENDED_PART_STATUSES). */
const ENDED = new Set(["COMPLETED", "SCRAPPED", "CANCELLED", "SHIPPED", "IN_STOCK", "AWAITING_PICKUP", "RMA_CLOSED", "DISMANTLED"]);
/** Statuses that count as built (PROGRESS_DONE_STATUSES). */
const BUILT = new Set(["COMPLETED", "DISMANTLED", "SHIPPED", "IN_STOCK", "AWAITING_PICKUP"]);
const SCRAP = "SCRAP";

const shortCloseWorkOrderOptions = (id: string) =>
    queryOptions({
        queryKey: ["short-close", "work-order", id] as const,
        queryFn: () => api.api_WorkOrders_retrieve({ params: { id } }),
    });
const shortClosePartsOptions = (id: string) =>
    queryOptions({
        queryKey: ["short-close", "parts", id] as const,
        queryFn: () => api.api_Parts_list({ queries: { work_order: id, limit: 1000 } }),
    });
const shortCloseTargetsOptions = (id: string) =>
    queryOptions({
        queryKey: ["short-close", "targets", id] as const,
        queryFn: () => api.api_WorkOrders_short_close_targets_retrieve({ params: { id } }),
    });

export function ShortCloseDialog({ workOrderId, open, onOpenChange, onDone }: {
    workOrderId: string;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onDone?: () => void;
}) {
    const queryClient = useQueryClient();
    const { data: wo } = useQuery({ ...shortCloseWorkOrderOptions(workOrderId), enabled: open });
    const { data: partsPage } = useQuery({ ...shortClosePartsOptions(workOrderId), enabled: open });
    const { data: targetData } = useQuery({ ...shortCloseTargetsOptions(workOrderId), enabled: open });

    const parts = useMemo(() => partsPage?.results ?? [], [partsPage]);
    const unfinished = parts.filter((p) => !ENDED.has(p.part_status ?? ""));
    const built = parts.filter((p) => BUILT.has(p.part_status ?? "")).length;
    const targets = targetData?.targets ?? [];
    /** The targets a unit may move to (same customer or on no order; a customer's own unit only to theirs). */
    const targetsFor = (partId: string) => {
        const ok = new Set(targetData?.allowed?.[partId] ?? []);
        return targets.filter((t) => ok.has(t.id));
    };
    // "Set all" offers only targets every unit may take.
    const commonTargets = targets.filter((t) => unfinished.every((p) => (targetData?.allowed?.[p.id] ?? []).includes(t.id)));
    const targetLabel = (t: { ERP_id: string; customer_name?: string | null }) =>
        `Move to ${t.ERP_id}${t.customer_name ? ` (${t.customer_name})` : " (no order)"}`;

    const [reason, setReason] = useState("");
    /** part id -> "SCRAP" or a target work order id */
    const [choice, setChoice] = useState<Record<string, string>>({});
    const setAll = (v: string) => setChoice(Object.fromEntries(unfinished.map((p) => [p.id, v])));
    const allChosen = unfinished.every((p) => choice[p.id]);

    /** target work order id -> raise its quantity by the units moved in (unanswered until set) */
    const [raise, setRaise] = useState<Record<string, boolean>>({});
    /** give the unbuilt units back to the order line (unanswered until set) */
    const [giveBack, setGiveBack] = useState<boolean | null>(null);
    const movedInto = targets
        .map((t) => ({ target: t, count: unfinished.filter((p) => choice[p.id] === t.id).length }))
        .filter((m) => m.count > 0);
    const shortfall = Math.max(0, (wo?.quantity ?? 0) - built);
    // Units moved to a raised work order on the same line are planned there already.
    const covered = movedInto
        .filter((m) => raise[m.target.id] && wo?.order_line && m.target.order_line === wo.order_line)
        .reduce((n, m) => n + m.count, 0);
    const returnable = Math.max(0, shortfall - covered);
    const askGiveBack = !!wo?.order_line && returnable > 0;
    const answered = movedInto.every((m) => typeof raise[m.target.id] === "boolean")
        && (!askGiveBack || giveBack !== null);

    const submit = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: () => api.api_WorkOrders_short_close_create({
            reason: reason.trim(),
            return_shortfall: askGiveBack ? giveBack : null,
            raise_targets: movedInto.map((m) => ({ work_order: m.target.id, raise_quantity: raise[m.target.id] })),
            dispositions: unfinished.map((p) => choice[p.id] === SCRAP
                ? { part: p.id, action: "SCRAP" as const }
                : { part: p.id, action: "MOVE" as const, target_work_order: choice[p.id] }),
        }, { params: { id: workOrderId }, headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" } }),
        onSuccess: () => {
            toast.success("Work order short-closed");
            onOpenChange(false);
            setReason("");
            setChoice({});
            setRaise({});
            setGiveBack(null);
            queryClient.invalidateQueries({ predicate: (q) => JSON.stringify(q.queryKey).includes(workOrderId) });
            onDone?.();
        },
        onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't short-close the work order"),
    });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
                <DialogHeader>
                    <DialogTitle>Short-close {wo?.ERP_id ?? "work order"}</DialogTitle>
                    <DialogDescription>
                        Complete it with fewer built than planned: {built} of {wo?.quantity ?? "—"} built.
                        Each unfinished unit is scrapped or moved to another open work order on the same process,
                        where it carries on from its current step.
                    </DialogDescription>
                </DialogHeader>

                {built === 0 && partsPage ? (
                    <p className="text-sm text-muted-foreground">Nothing on this work order has finished — cancel it instead.</p>
                ) : (
                    <div className="space-y-4">
                        {unfinished.length > 0 && (
                            <div className="space-y-2">
                                <div className="flex items-center justify-between gap-2">
                                    <Label>Unfinished units ({unfinished.length})</Label>
                                    <Select onValueChange={setAll}>
                                        <SelectTrigger className="h-8 w-48"><SelectValue placeholder="Set all to…" /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value={SCRAP}>Scrap</SelectItem>
                                            {commonTargets.map((t) => <SelectItem key={t.id} value={t.id}>{targetLabel(t)}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <ul className="divide-y rounded-md border">
                                    {unfinished.map((p) => (
                                        <li key={p.id} className="flex flex-wrap items-center gap-2 p-2 text-sm">
                                            <span className="min-w-0 flex-1">
                                                <span className="font-mono">{p.ERP_id}</span>
                                                <span className="ml-2 text-xs text-muted-foreground">
                                                    {p.step_name ?? "—"} · {(p.part_status ?? "").replace(/_/g, " ").toLowerCase()}
                                                </span>
                                            </span>
                                            <Select value={choice[p.id] ?? ""} onValueChange={(v) => setChoice((c) => ({ ...c, [p.id]: v }))}>
                                                <SelectTrigger className="h-8 w-48"><SelectValue placeholder="Scrap or move…" /></SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value={SCRAP}>Scrap</SelectItem>
                                                    {targetsFor(p.id).map((t) => <SelectItem key={t.id} value={t.id}>{targetLabel(t)}</SelectItem>)}
                                                </SelectContent>
                                            </Select>
                                        </li>
                                    ))}
                                </ul>
                                {targets.length === 0 ? (
                                    <p className="text-xs text-muted-foreground">
                                        No other open work order for this customer runs this process, so units can only be scrapped here.
                                    </p>
                                ) : (
                                    <p className="text-xs text-muted-foreground">
                                        Units move only to work for the same customer or on no order; a customer&rsquo;s own unit only to theirs.
                                    </p>
                                )}
                            </div>
                        )}
                        {movedInto.map((m) => (
                            <YesNo
                                key={m.target.id}
                                id={`raise-${m.target.id}`}
                                question={`Raise ${m.target.ERP_id}'s quantity from ${m.target.quantity} to ${(m.target.quantity ?? 0) + m.count} for the ${m.count} unit${m.count === 1 ? "" : "s"} moved onto it?`}
                                yes={`Yes — ${m.target.ERP_id} plans for them`}
                                no={`No — leave ${m.target.ERP_id} at ${m.target.quantity}`}
                                value={raise[m.target.id] ?? null}
                                onChange={(v) => setRaise((r) => ({ ...r, [m.target.id]: v }))}
                            />
                        ))}
                        {askGiveBack && (
                            <YesNo
                                id="give-back"
                                question={`Give the ${returnable} unit${returnable === 1 ? "" : "s"} it didn't build back to the order line, as demand still to plan?`}
                                yes="Yes — the customer still wants them"
                                no="No — the line is done with them"
                                value={giveBack}
                                onChange={setGiveBack}
                            />
                        )}
                        <div className="space-y-1">
                            <Label htmlFor="short-close-reason">Why is it closing short?</Label>
                            <Textarea id="short-close-reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
                        </div>
                    </div>
                )}

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Go back</Button>
                    <Button
                        disabled={built === 0 || !reason.trim() || !allChosen || !answered || submit.isPending}
                        onClick={() => submit.mutate()}
                    >
                        Short-close
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

/** A question with no default answer: neither option is selected until someone picks. */
function YesNo({ id, question, yes, no, value, onChange }: {
    id: string; question: string; yes: string; no: string;
    value: boolean | null; onChange: (v: boolean) => void;
}) {
    return (
        <div className="space-y-2 rounded-md border p-3">
            <Label>{question}</Label>
            <RadioGroup value={value === null ? "" : value ? "yes" : "no"} onValueChange={(v) => onChange(v === "yes")}>
                <div className="flex items-center gap-2">
                    <RadioGroupItem value="yes" id={`${id}-yes`} />
                    <Label htmlFor={`${id}-yes`} className="font-normal">{yes}</Label>
                </div>
                <div className="flex items-center gap-2">
                    <RadioGroupItem value="no" id={`${id}-no`} />
                    <Label htmlFor={`${id}-no`} className="font-normal">{no}</Label>
                </div>
            </RadioGroup>
        </div>
    );
}
