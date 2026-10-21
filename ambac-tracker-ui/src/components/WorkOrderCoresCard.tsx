import { useState } from "react";
import { useRetrieveCore } from "@/hooks/useRetrieveCore";
import { Link } from "@tanstack/react-router";
import { toast } from "sonner";
import { Hammer, PackageCheck, Play, Truck, Wrench } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { coreStageLabel, coreStageVariant } from "@/lib/reman/core-stages";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
    Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from "@/components/ui/tooltip";

import { useCoreLifecycleAction, useReleaseCore } from "@/hooks/useReleaseCore";
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
    // The customer's answer, recorded by staff: who answered, how, and the reference.
    const [answering, setAnswering] = useState<{ core: WorkOrderCore; approved: boolean } | null>(null);
    const [returning, setReturning] = useState<WorkOrderCore | null>(null);
    const release = useReleaseCore();
    const lifecycle = useCoreLifecycleAction();
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

    return (
        <TooltipProvider>
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
                    <div className="w-full overflow-x-auto rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow>
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
                                                            <Button
                                                                size="sm" variant="ghost" disabled={busy}
                                                                onClick={() => act(core,
                                                                    { id, action: "request_authorisation" },
                                                                    "sent for customer authorisation")}
                                                            >
                                                                Authorise…
                                                            </Button>
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
                                                                    onClick={() => doRelease(core, "inventory")}
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
                    coreId={String(answering.core.id)}
                    coreNumber={answering.core.core_number}
                    approved={answering.approved}
                    pending={lifecycle.isPending}
                    onCancel={() => setAnswering(null)}
                    onConfirm={(fields) => {
                        act(answering.core,
                            { id: String(answering.core.id), action: "record_authorisation",
                              approved: answering.approved, ...fields },
                            answering.approved ? "approved — rebuild resumed" : "declined");
                        setAnswering(null);
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
export function CustomerAnswerDialog({ coreId, coreNumber, approved, pending, onCancel, onConfirm }: {
    coreId: string;
    coreNumber: string;
    approved: boolean;
    pending: boolean;
    onCancel: () => void;
    onConfirm: (f: { contact: string; method: string; reference: string; note: string }) => void;
}) {
    const [contact, setContact] = useState("");
    const [method, setMethod] = useState("");
    const [reference, setReference] = useState("");
    const [note, setNote] = useState("");
    // What they're answering: each code, its name, and the finding behind it — so the
    // person recording the answer sees what was agreed to.
    const { data: core } = useRetrieveCore(coreId);
    const scope = core?.awaiting_authorisation ?? [];
    return (
        <Dialog open onOpenChange={(o) => { if (!o) onCancel(); }}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>
                        {coreNumber} — customer {approved ? "approved" : "declined"}
                    </DialogTitle>
                    <DialogDescription>
                        {approved
                            ? "The repairs waiting on their answer are approved and the rebuild resumes."
                            : "The unit goes back to them unrepaired."}
                    </DialogDescription>
                </DialogHeader>
                {scope.length > 0 && (
                    <ul className="space-y-1 rounded-md border bg-muted/30 p-2 text-sm">
                        {scope.map((item) => (
                            <li key={item.code}>
                                <span className="font-mono text-xs">{item.code}</span>
                                {item.name ? ` · ${item.name}` : ""}
                                {item.why.length > 0 && (
                                    <span className="text-muted-foreground"> — {item.why.join("; ")}</span>
                                )}
                            </li>
                        ))}
                    </ul>
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
                        onClick={() => onConfirm({ contact, method, reference, note })}>
                        Record {approved ? "approval" : "decline"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
