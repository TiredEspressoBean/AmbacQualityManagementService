import { useState } from "react";
import { useQueries } from "@tanstack/react-query";
import { RequestAuthorisationButton } from "@/components/reman/RequestAuthorisationButton";
import { retrieveCoreOptions } from "@/hooks/useRetrieveCore";
import { Link } from "@tanstack/react-router";
import { toast } from "sonner";
import { Hammer, PackageCheck, Play, Truck, Wrench } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { ReportButton } from "@/components/reports/ReportButton";
import { coreStageLabel, coreStageVariant } from "@/lib/reman/core-stages";
import { Button } from "@/components/ui/button";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
    AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
    Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from "@/components/ui/tooltip";

import { useBulkCoreAuthorisation, useCoreLifecycleAction, useReleaseCore } from "@/hooks/useReleaseCore";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ShipDialog } from "@/components/shipping/ShipDialog";
import { useWorkUnit } from "@/hooks/useWorkUnit";
import { apiErrorBody, apiErrorField } from "@/lib/api/describeApiError";
import type { Schema } from "@/lib/api/types";

type WorkOrderCore = NonNullable<Schema<"WorkOrder">["cores"]>[number];


/**
 * The cores on a teardown work order.
 *
 * A teardown WO's subjects are cores rather than parts, so without this the control
 * page renders an empty job. This is also where each core's exit is decided — which
 * is not a free choice: a unit that goes back to its customer must be rebuilt, and
 * anything else is a source of parts. The buttons reflect that rather than offering
 * both and letting someone pick wrong.
 */
export function WorkOrderCoresCard(
    { cores, workOrderId }: { cores: WorkOrderCore[]; workOrderId?: string },
) {
    const [pending, setPending] = useState<string | null>(null);
    // Harvest consumes the unit, so it is confirmed before it runs.
    const [harvesting, setHarvesting] = useState<WorkOrderCore | null>(null);
    // The customer's answer, recorded by staff: who answered, how, and the reference.
    const [answering, setAnswering] = useState<{ core: WorkOrderCore; approved: boolean } | null>(null);
    const [returning, setReturning] = useState<WorkOrderCore | null>(null);
    // A customer's lot: several of their units sent and answered together.
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [bulkAnswer, setBulkAnswer] = useState<boolean | null>(null);
    const release = useReleaseCore();
    const lifecycle = useCoreLifecycleAction();
    const bulk = useBulkCoreAuthorisation();
    // Teardown and rebuild are worked in the DWI operator runtime, at the step the unit
    // is at — a core is a part, so it opens like any part's work.
    const { workUnit, pending: opening } = useWorkUnit();
    const workable = (status?: string) =>
        status === "RECEIVED" || status === "IN_DISASSEMBLY" || status === "IN_REBUILD";

    if (!cores || cores.length === 0) return null;

    function onError(err: unknown) {
        const body = apiErrorBody(err);
        toast.error(
            apiErrorField(body, "detail") ??
            (err as Error)?.message ??
            "unknown error",
        );
    }

    function doRelease(core: WorkOrderCore, to: "rebuild" | "inventory") {
        setPending(String(core.id));
        release.mutate(
            { id: String(core.id), to },
            {
                onSuccess: (data) => {
                    if (data.to === "rebuild") {
                        const n = data.result.expected_repair_count;
                        toast.success(
                            `${core.core_number} released into rebuild at ${data.result.first_step ?? "?"} — ` +
                            `${n} expected repair${n === 1 ? "" : "s"}`,
                        );
                    } else {
                        toast.success(
                            `${core.core_number} harvested — ${data.result.accepted_count} components to stock`,
                        );
                    }
                },
                onError,
                onSettled: () => setPending(null),
            },
        );
    }

    function act(
        core: WorkOrderCore,
        v: Parameters<typeof lifecycle.mutate>[0],
        message: string,
    ) {
        setPending(String(core.id));
        lifecycle.mutate(v, {
            onSuccess: () => toast.success(`${core.core_number} — ${message}`),
            onError,
            onSettled: () => setPending(null),
        });
    }

    const awaiting = cores.filter((c) => c.status === "DISASSEMBLED").length;

    // A unit can join a lot while its customer's answer is still to be asked for or given.
    const lotable = (c: WorkOrderCore) =>
        !!c.returns_to_customer && (c.status === "IN_REBUILD" || c.status === "AWAITING_AUTHORISATION");
    const anyLotable = cores.some(lotable);
    const picked = cores.filter((c) => selected.has(String(c.id)));
    const pickedIds = picked.map((c) => String(c.id));
    const pickedStatus = new Set(picked.map((c) => c.status));
    const pickedCustomers = new Set(picked.map((c) => c.customer ?? null));
    // A lot is one customer's units at one stage; anything else would be refused anyway.
    const lotProblem = pickedCustomers.size > 1 ? "Choose one customer's units."
        : pickedStatus.size > 1 ? "Choose units at the same stage." : null;
    const toggle = (id: string, on: boolean) => setSelected((s) => {
        const next = new Set(s);
        if (on) next.add(id); else next.delete(id);
        return next;
    });
    function onBulkDone(message: string) {
        toast.success(message);
        setSelected(new Set());
    }

    return (
        <TooltipProvider>
            <AlertDialog open={harvesting !== null} onOpenChange={(o) => { if (!o) setHarvesting(null); }}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Harvest {harvesting?.core_number ?? "this core"}?</AlertDialogTitle>
                        <AlertDialogDescription>
                            The unit is consumed: it won't be rebuilt, and its usable components go
                            to stock. This can't be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={() => { if (harvesting) doRelease(harvesting, "inventory"); setHarvesting(null); }}>
                            Harvest for parts
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
            <Card>
                <CardHeader>
                    <CardTitle className="flex flex-wrap items-baseline gap-3">
                        <span>Cores</span>
                        <span className="text-sm font-normal text-muted-foreground tabular-nums">
                            {cores.length}
                            {awaiting > 0 ? ` · ${awaiting} awaiting release` : ""}
                        </span>
                    </CardTitle>
                    <CardDescription>
                        Teardown ends in one of two places, and which one follows from the
                        unit's arrangement: a core that goes back to its customer is rebuilt
                        on this same work order, and anything else is a source of parts.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {picked.length > 0 && (
                        <div className="mb-3 flex flex-wrap items-center gap-2 rounded-md border bg-muted/30 p-2 text-sm">
                            <span className="font-medium">{picked.length} selected</span>
                            {lotProblem ? (
                                <span className="text-muted-foreground">{lotProblem}</span>
                            ) : (
                                <>
                                    <ReportButton reportType="over_and_above_scope_lot"
                                        params={{ core_ids: pickedIds }} label="Scope for customer" />
                                    {pickedStatus.has("IN_REBUILD") && (
                                        <Button size="sm" variant="outline" disabled={bulk.isPending}
                                            onClick={() => bulk.mutate({ action: "request", coreIds: pickedIds }, {
                                                onSuccess: () => onBulkDone(`${picked.length} units sent for authorisation`),
                                                onError,
                                            })}>
                                            Send for authorisation
                                        </Button>
                                    )}
                                    {pickedStatus.has("AWAITING_AUTHORISATION") && (
                                        <>
                                            <Button size="sm" disabled={bulk.isPending}
                                                onClick={() => setBulkAnswer(true)}>
                                                Approved…
                                            </Button>
                                            <Button size="sm" variant="outline" disabled={bulk.isPending}
                                                onClick={() => setBulkAnswer(false)}>
                                                Declined…
                                            </Button>
                                        </>
                                    )}
                                </>
                            )}
                            <Button size="sm" variant="ghost" className="ml-auto"
                                onClick={() => setSelected(new Set())}>
                                Clear
                            </Button>
                        </div>
                    )}
                    <div className="w-full overflow-x-auto rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    {anyLotable && <TableHead className="w-8" />}
                                    <TableHead>Core</TableHead>
                                    <TableHead>Customer</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>At</TableHead>
                                    <TableHead>Components</TableHead>
                                    <TableHead>Exit</TableHead>
                                    <TableHead />
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {cores.map((core) => {
                                    const id = String(core.id);
                                    const harvested = core.harvested_component_count ?? 0;
                                    const usable = core.usable_component_count ?? 0;
                                    const ready = core.status === "DISASSEMBLED";
                                    const busy = pending === id;
                                    return (
                                        <TableRow key={id}>
                                            {anyLotable && (
                                                <TableCell>
                                                    {lotable(core) && (
                                                        <Checkbox
                                                            aria-label={`Select ${core.core_number}`}
                                                            checked={selected.has(id)}
                                                            onCheckedChange={(v) => toggle(id, v === true)}
                                                        />
                                                    )}
                                                </TableCell>
                                            )}
                                            <TableCell className="font-mono text-sm font-medium">
                                                <Link
                                                    to="/reman/cores/$id"
                                                    params={{ id }}
                                                    className="underline decoration-dotted underline-offset-4"
                                                >
                                                    {core.core_number}
                                                </Link>
                                            </TableCell>
                                            <TableCell>{core.customer_name || "—"}</TableCell>
                                            <TableCell>
                                                <Badge variant={coreStageVariant(core.status)}>
                                                    {coreStageLabel(core.status)}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-sm text-muted-foreground">
                                                {core.step_name || "—"}
                                            </TableCell>
                                            <TableCell className="tabular-nums">
                                                {harvested === 0 ? "—" : `${usable} / ${harvested}`}
                                            </TableCell>
                                            <TableCell className="text-sm">
                                                {core.returns_to_customer ? (
                                                    <span>Rebuild &amp; return</span>
                                                ) : (
                                                    <span className="text-muted-foreground">
                                                        Rebuild or harvest to stock
                                                    </span>
                                                )}
                                            </TableCell>
                                            <TableCell className="whitespace-nowrap text-right">
                                                {workOrderId && core.part && workable(core.status) && (
                                                    <Button
                                                        size="sm" className="mr-1" disabled={opening}
                                                        onClick={() => workUnit(String(core.part), workOrderId)}
                                                    >
                                                        <Play className="mr-1 h-4 w-4" />
                                                        Work
                                                    </Button>
                                                )}
                                                {core.status === "IN_DISASSEMBLY" ? (
                                                    // Closing the teardown is what makes a unit's exit
                                                    // decidable — every release, authorisation and
                                                    // return downstream needs DISASSEMBLED.
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <span>
                                                                <Button
                                                                    size="sm" variant="outline" disabled={busy}
                                                                    onClick={() => act(core,
                                                                        { id, action: "complete_disassembly" },
                                                                        "teardown complete — ready for its exit")}
                                                                >
                                                                    <PackageCheck className="mr-1 h-4 w-4" />
                                                                    {busy ? "Closing…" : "Complete teardown"}
                                                                </Button>
                                                            </span>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                            Everything worth keeping is off the unit. This is
                                                            what opens its exit — rebuild, or harvest to stock.
                                                        </TooltipContent>
                                                    </Tooltip>
                                                ) : core.status === "IN_REBUILD" ? (
                                                    <span className="inline-flex gap-1">
                                                        <Button size="sm" variant="outline" asChild>
                                                            <Link to="/reman/cores/$id/rebuild" params={{ id }}>
                                                                <Wrench className="mr-1 h-4 w-4" />
                                                                Plan
                                                            </Link>
                                                        </Button>
                                                        {core.returns_to_customer && (
                                                            <RequestAuthorisationButton coreId={id} coreNumber={core.core_number} />
                                                        )}
                                                    </span>
                                                ) : core.status === "AWAITING_AUTHORISATION" ? (
                                                    // The conversation happened elsewhere; these
                                                    // record what the customer said.
                                                    <span className="inline-flex gap-1">
                                                        <Button
                                                            size="sm" disabled={busy}
                                                            onClick={() => setAnswering({ core, approved: true })}
                                                        >
                                                            Approved…
                                                        </Button>
                                                        <Button
                                                            size="sm" variant="outline" disabled={busy}
                                                            onClick={() => setAnswering({ core, approved: false })}
                                                        >
                                                            Declined…
                                                        </Button>
                                                    </span>
                                                ) : core.status === "REBUILT" || core.status === "DECLINED" ? (
                                                    // A return is a shipment like any other, so
                                                    // the packing list and CoC print for it.
                                                    <Button
                                                        size="sm" disabled={busy}
                                                        onClick={() => setReturning(core)}
                                                    >
                                                        <Truck className="mr-1 h-4 w-4" />
                                                        Return
                                                    </Button>
                                                ) : ready && core.returns_to_customer ? (
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <span>
                                                                <Button
                                                                    size="sm"
                                                                    onClick={() => doRelease(core, "rebuild")}
                                                                    disabled={busy}
                                                                >
                                                                    <Hammer className="mr-1 h-4 w-4" />
                                                                    {busy ? "Releasing…" : "Release into rebuild"}
                                                                </Button>
                                                            </span>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                            Stays on this work order — the unit keeps one thread
                                                            from arrival to shipment.
                                                        </TooltipContent>
                                                    </Tooltip>
                                                ) : ready ? (
                                                    // Exchange: the shop's unit. Normally rebuilt to
                                                    // stock, keeping its identity; harvested when its
                                                    // body fails or cores are surplus. A planner picks.
                                                    <span className="inline-flex gap-1">
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <span>
                                                                <Button
                                                                    size="sm"
                                                                    onClick={() => doRelease(core, "rebuild")}
                                                                    disabled={busy}
                                                                >
                                                                    <Hammer className="mr-1 h-4 w-4" />
                                                                    {busy ? "Releasing…" : "Rebuild to stock"}
                                                                </Button>
                                                            </span>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                            Rebuilt as the same unit and stocked as reman
                                                            finished goods, ready for the next exchange.
                                                        </TooltipContent>
                                                    </Tooltip>
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <span>
                                                                <Button
                                                                    size="sm"
                                                                    variant="outline"
                                                                    onClick={() => setHarvesting(core)}
                                                                    disabled={busy}
                                                                >
                                                                    <PackageCheck className="mr-1 h-4 w-4" />
                                                                    {busy ? "Releasing…" : "Release to inventory"}
                                                                </Button>
                                                            </span>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                            Accepts {usable} usable component
                                                            {usable === 1 ? "" : "s"} into stock. The core is
                                                            consumed.
                                                        </TooltipContent>
                                                    </Tooltip>
                                                    </span>
                                                ) : (
                                                    <span className="text-sm text-muted-foreground">—</span>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>
            {answering && (
                <CustomerAnswerDialog
                    coreIds={[String(answering.core.id)]}
                    title={answering.core.core_number}
                    approved={answering.approved}
                    pending={lifecycle.isPending}
                    onCancel={() => setAnswering(null)}
                    onConfirm={({ declinedByCore, ...fields }) => {
                        const id = String(answering.core.id);
                        act(answering.core,
                            { id, action: "record_authorisation", approved: answering.approved,
                              declinedCodes: declinedByCore[id] ?? [], ...fields },
                            answering.approved ? "answer recorded" : "declined");
                        setAnswering(null);
                    }}
                />
            )}
            {bulkAnswer !== null && picked.length > 0 && (
                <CustomerAnswerDialog
                    coreIds={pickedIds}
                    title={`${picked.length} units`}
                    approved={bulkAnswer}
                    pending={bulk.isPending}
                    onCancel={() => setBulkAnswer(null)}
                    onConfirm={({ declinedByCore, ...fields }) => {
                        const n = picked.length;
                        bulk.mutate({ action: "record", coreIds: pickedIds, approved: bulkAnswer,
                                      declinedByCore, ...fields }, {
                            onSuccess: () => onBulkDone(
                                `${n} units — ${bulkAnswer ? "answer recorded" : "declined"}`),
                            onError,
                        });
                        setBulkAnswer(null);
                    }}
                />
            )}
            {returning && (
                <ShipDialog
                    group={{
                        order_id: null, order_number: null,
                        customer_id: returning.customer ?? null,
                        customer_name: returning.customer_name ?? null,
                        requires_coc: false, parts: [], lots: [],
                    }}
                    partIds={[String(returning.part)]} initialLots={[]} open
                    onOpenChange={(o) => { if (!o) setReturning(null); }}
                    onShipped={() => setReturning(null)}
                />
            )}
        </TooltipProvider>
    );
}

/** Record what the customer said. The conversation happened elsewhere (phone, email,
 *  a PO); this is the production record of it — who answered, how, and the reference
 *  to trace it. Nobody at the customer needs a login for it to be on record. */
export function CustomerAnswerDialog({ coreIds, title, approved, pending, onCancel, onConfirm }: {
    /** One unit, or a customer's lot answered together. */
    coreIds: string[];
    title: string;
    /** Approved… records the answer item by item; Declined… declines each unit whole. */
    approved: boolean;
    pending: boolean;
    onCancel: () => void;
    onConfirm: (f: {
        contact: string; method: string; reference: string; note: string;
        /** Core id → the repairs declined on that unit. */
        declinedByCore: Record<string, string[]>;
    }) => void;
}) {
    const [contact, setContact] = useState("");
    const [method, setMethod] = useState("");
    const [reference, setReference] = useState("");
    const [note, setNote] = useState("");
    // Core id → codes the customer declined. Everything starts approved: most answers are
    // "yes", so the common case is one click.
    const [declined, setDeclined] = useState<Record<string, string[]>>({});
    // What each unit is waiting on: each code, its name, the finding behind it, and
    // whether the shop marked it required — so whoever records it sees what's agreed.
    const units = useQueries({
        queries: coreIds.map((id) => retrieveCoreOptions(id)),
        combine: (rs) => rs.map((r) => r.data).filter((c): c is NonNullable<typeof c> => !!c),
    });
    const many = coreIds.length > 1;
    const isDeclined = (id: string, code: string) => (declined[id] ?? []).includes(code);
    const setItem = (id: string, code: string, approve: boolean) => setDeclined((d) => {
        const now = new Set(d[id] ?? []);
        if (approve) now.delete(code); else now.add(code);
        return { ...d, [id]: [...now] };
    });
    // Units a declined REQUIRED repair sends back unrepaired.
    const goingBack = approved ? units.filter((u) =>
        (u.awaiting_authorisation ?? []).some((i) => i.required && isDeclined(String(u.id), i.code))) : [];
    // The lot grid's columns: every repair waiting on any of the units.
    const columns = Array.from(new Map(units.flatMap((u) => u.awaiting_authorisation ?? [])
        .map((i) => [i.code, i] as const)).values());
    const setColumn = (code: string, approve: boolean) => units.forEach((u) => {
        if ((u.awaiting_authorisation ?? []).some((i) => i.code === code)) setItem(String(u.id), code, approve);
    });
    const allBack = approved && units.length > 0 && goingBack.length === units.length;
    return (
        <Dialog open onOpenChange={(o) => { if (!o) onCancel(); }}>
            <DialogContent className={many && approved ? "max-w-3xl" : undefined}>
                <DialogHeader>
                    <DialogTitle>
                        {title} — customer {approved ? "answered" : "declined"}
                    </DialogTitle>
                    <DialogDescription>
                        {approved
                            ? "Untick any repair they declined. The rest are approved and the rebuild resumes; a declined repair is left out."
                            : many ? "Each unit goes back to them unrepaired." : "The unit goes back to them unrepaired."}
                    </DialogDescription>
                </DialogHeader>
                {approved && !many && units[0] && (
                    <ul className="space-y-2 rounded-md border p-2 text-sm">
                        {(units[0].awaiting_authorisation ?? []).map((item) => {
                            const id = String(units[0].id);
                            const off = isDeclined(id, item.code);
                            return (
                                <li key={item.code} className="flex items-start gap-2">
                                    <Checkbox
                                        aria-label={`Approve ${item.code}`}
                                        checked={!off}
                                        onCheckedChange={(v) => setItem(id, item.code, v === true)}
                                        className="mt-0.5"
                                    />
                                    <div>
                                        <span className="font-mono text-xs">{item.code}</span>
                                        {item.name ? ` · ${item.name}` : ""}
                                        {item.why.length > 0 && (
                                            <span className="text-muted-foreground"> — {item.why.join("; ")}</span>
                                        )}
                                        {off && (
                                            <p className={item.required ? "text-xs text-destructive" : "text-xs text-muted-foreground"}>
                                                {item.required
                                                    ? "Required for the rebuild: declining it returns the unit unrepaired."
                                                    : "Declined: the unit is rebuilt without it."}
                                            </p>
                                        )}
                                    </div>
                                </li>
                            );
                        })}
                    </ul>
                )}
                {approved && many && (
                    <div className="overflow-x-auto rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Unit</TableHead>
                                    {columns.map((c) => (
                                        <TableHead key={c.code} className="text-center">
                                            <div className="font-mono text-xs">{c.code}</div>
                                            {c.required && <div className="text-[10px] font-normal text-muted-foreground">required</div>}
                                            <div className="mt-1 flex justify-center gap-1">
                                                <Button size="sm" variant="ghost" className="h-6 px-1.5 text-xs"
                                                    onClick={() => setColumn(c.code, true)}>All</Button>
                                                <Button size="sm" variant="ghost" className="h-6 px-1.5 text-xs"
                                                    onClick={() => setColumn(c.code, false)}>None</Button>
                                            </div>
                                        </TableHead>
                                    ))}
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {units.map((u) => {
                                    const id = String(u.id);
                                    const codes = new Set((u.awaiting_authorisation ?? []).map((i) => i.code));
                                    return (
                                        <TableRow key={id}>
                                            <TableCell className="font-mono text-xs">
                                                {u.serial_number || u.core_number}
                                                {goingBack.includes(u) && (
                                                    <div className="font-sans text-[10px] text-destructive">goes back unrepaired</div>
                                                )}
                                            </TableCell>
                                            {columns.map((c) => (
                                                <TableCell key={c.code} className="text-center">
                                                    {codes.has(c.code) ? (
                                                        <Checkbox
                                                            aria-label={`Approve ${c.code} on ${u.core_number}`}
                                                            checked={!isDeclined(id, c.code)}
                                                            onCheckedChange={(v) => setItem(id, c.code, v === true)}
                                                        />
                                                    ) : <span className="text-muted-foreground">—</span>}
                                                </TableCell>
                                            ))}
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </div>
                )}
                {!approved && many && (
                    <p className="rounded-md border bg-muted/30 p-2 font-mono text-xs">
                        {units.map((u) => u.core_number).join(", ")}
                    </p>
                )}
                {goingBack.length > 0 && (
                    <p className="rounded-md border border-destructive/40 bg-destructive/5 p-2 text-sm text-destructive">
                        {many
                            ? `${goingBack.length} unit(s) go back unrepaired: a required repair was declined.`
                            : "The unit goes back unrepaired: a required repair was declined."}
                    </p>
                )}
                <div className="grid gap-3">
                    <div className="grid gap-1.5">
                        <Label htmlFor="ans-contact">Who answered</Label>
                        <Input id="ans-contact" value={contact} onChange={(e) => setContact(e.target.value)}
                            placeholder="e.g. Pat Ruiz, fleet maintenance" />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div className="grid gap-1.5">
                            <Label htmlFor="ans-method">How</Label>
                            <Input id="ans-method" value={method} onChange={(e) => setMethod(e.target.value)}
                                placeholder="phone, email, PO" />
                        </div>
                        <div className="grid gap-1.5">
                            <Label htmlFor="ans-ref">Reference</Label>
                            <Input id="ans-ref" value={reference} onChange={(e) => setReference(e.target.value)}
                                placeholder="PO or email ref" />
                        </div>
                    </div>
                    <div className="grid gap-1.5">
                        <Label htmlFor="ans-note">Note (optional)</Label>
                        <Input id="ans-note" value={note} onChange={(e) => setNote(e.target.value)} />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={onCancel}>Cancel</Button>
                    <Button disabled={pending || !contact.trim()}
                        variant={!approved || allBack ? "destructive" : "default"}
                        onClick={() => onConfirm({ contact, method, reference, note, declinedByCore: declined })}>
                        {!approved || allBack ? "Record decline" : "Record answer"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
