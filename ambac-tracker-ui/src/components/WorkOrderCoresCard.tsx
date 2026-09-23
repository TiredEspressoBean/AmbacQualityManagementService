import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { toast } from "sonner";
import { Hammer, PackageCheck, Truck, Wrench } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
    Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from "@/components/ui/tooltip";

import { useCoreLifecycleAction, useReleaseCore } from "@/hooks/useReleaseCore";
import { apiErrorBody, apiErrorField } from "@/lib/api/describeApiError";
import type { Schema } from "@/lib/api/types";

type WorkOrderCore = NonNullable<Schema<"WorkOrder">["cores"]>[number];

const STATUS_LABEL: Record<string, string> = {
    RECEIVED: "Received",
    IN_DISASSEMBLY: "In disassembly",
    DISASSEMBLED: "Disassembled",
    IN_REBUILD: "In rebuild",
    REBUILT: "Rebuilt",
    RETURNED: "Returned",
    AWAITING_AUTHORISATION: "Awaiting authorisation",
    DECLINED: "Scope declined",
    RETURNED_UNREPAIRED: "Returned unrepaired",
    HARVESTED: "Harvested",
    SCRAPPED: "Scrapped",
};

function statusVariant(status: string): "default" | "secondary" | "outline" | "destructive" {
    if (status === "SCRAPPED" || status === "DECLINED") return "destructive";
    if (status === "AWAITING_AUTHORISATION") return "outline";
    if (status === "RETURNED" || status === "RETURNED_UNREPAIRED") return "secondary";
    if (status === "DISASSEMBLED") return "outline";
    if (status === "IN_REBUILD" || status === "REBUILT") return "default";
    return "secondary";
}

/**
 * The cores on a teardown work order.
 *
 * A teardown WO's subjects are cores rather than parts, so without this the control
 * page renders an empty job. This is also where each core's exit is decided — which
 * is not a free choice: a unit that goes back to its customer must be rebuilt, and
 * anything else is a source of parts. The buttons reflect that rather than offering
 * both and letting someone pick wrong.
 */
export function WorkOrderCoresCard({ cores }: { cores: WorkOrderCore[] }) {
    const [pending, setPending] = useState<string | null>(null);
    const release = useReleaseCore();
    const lifecycle = useCoreLifecycleAction();

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
                    if (to === "rebuild") {
                        const d = data as { first_step?: string; operation_count?: number };
                        toast.success(
                            `${core.core_number} released into rebuild — ${d.operation_count ?? 0} ` +
                            `operations, starting at ${d.first_step ?? "?"}`,
                        );
                    } else {
                        const d = data as { accepted_count?: number };
                        toast.success(
                            `${core.core_number} harvested — ${d.accepted_count ?? 0} components to stock`,
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
                                                <Badge variant={statusVariant(core.status ?? "")}>
                                                    {STATUS_LABEL[core.status ?? ""] ?? core.status}
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
                                                        Harvest to stock
                                                    </span>
                                                )}
                                            </TableCell>
                                            <TableCell className="whitespace-nowrap text-right">
                                                {core.status === "IN_REBUILD" ? (
                                                    <span className="inline-flex gap-1">
                                                        <Button size="sm" variant="outline" asChild>
                                                            <Link to="/reman/cores/$id/rebuild" params={{ id }}>
                                                                <Wrench className="mr-1 h-4 w-4" />
                                                                Plan
                                                            </Link>
                                                        </Button>
                                                        <Button
                                                            size="sm" variant="ghost" disabled={busy}
                                                            onClick={() => act(core,
                                                                { id, action: "request_authorisation" },
                                                                "sent for customer authorisation")}
                                                        >
                                                            Authorise…
                                                        </Button>
                                                    </span>
                                                ) : core.status === "AWAITING_AUTHORISATION" ? (
                                                    // The conversation happened elsewhere; these
                                                    // record what the customer said.
                                                    <span className="inline-flex gap-1">
                                                        <Button
                                                            size="sm" disabled={busy}
                                                            onClick={() => act(core,
                                                                { id, action: "record_authorisation", approved: true },
                                                                "scope approved — rebuild resumed")}
                                                        >
                                                            Approved
                                                        </Button>
                                                        <Button
                                                            size="sm" variant="outline" disabled={busy}
                                                            onClick={() => act(core,
                                                                { id, action: "record_authorisation", approved: false },
                                                                "scope declined")}
                                                        >
                                                            Declined
                                                        </Button>
                                                    </span>
                                                ) : core.status === "REBUILT" || core.status === "DECLINED" ? (
                                                    <Button
                                                        size="sm" disabled={busy}
                                                        onClick={() => act(core, { id, action: "return" },
                                                            core.status === "REBUILT"
                                                                ? "returned to customer"
                                                                : "returned unrepaired")}
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
        </TooltipProvider>
    );
}
