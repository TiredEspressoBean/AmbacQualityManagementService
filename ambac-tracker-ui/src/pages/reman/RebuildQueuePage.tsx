import { Link } from "@tanstack/react-router";
import { format } from "date-fns";
import { Wrench } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

import { useRetrieveCores } from "@/hooks/useRetrieveCores";

/**
 * Cores torn down and waiting to be released into rebuild.
 *
 * Exists so the loop is a queue somebody works rather than a URL you have to know.
 *
 * `IN_REBUILD` rather than `DISASSEMBLED`: teardown ends in one of two places, and only
 * a unit that goes back to its customer is rebuilt. An earlier version filtered on
 * DISASSEMBLED alone, which filled the queue with harvest cores nobody intended to
 * rebuild and gave no way to clear them. Releasing happens on the teardown work order,
 * where the operator actually is; this is the catch-up list of what has been released
 * and not yet planned.
 */
export function RebuildQueuePage() {
    const { data, isLoading, isError } = useRetrieveCores({
        status: "IN_REBUILD",
        ordering: "disassembly_completed_at",
        limit: 100,
        with_plan: true,
    });

    // Units with plan decisions still open first (oldest first within each), so the
    // queue reads as the work it is: a planned unit is on the floor, not waiting on you.
    const cores = [...(data?.results ?? [])].sort(
        (a, b) => Number((b.rebuild_decisions_open ?? 0) > 0) - Number((a.rebuild_decisions_open ?? 0) > 0));
    const toDecide = cores.filter((c) => (c.rebuild_decisions_open ?? 0) > 0).length;

    return (
        <div className="max-w-6xl mx-auto py-10 space-y-6">
            <div>
                <h1 className="text-2xl font-bold">Ready to rebuild</h1>
                <p className="text-muted-foreground">
                    Units released into rebuild. Those with plan decisions still open come
                    first, oldest first — a core sitting here is capital on a shelf. Cores
                    are released on their teardown work order.
                </p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-baseline gap-3">
                        <span>Queue</span>
                        <span className="text-sm font-normal text-muted-foreground tabular-nums">
                            {toDecide > 0 ? `${toDecide} to plan · ${cores.length} in rebuild` : `${cores.length} in rebuild, all planned`}
                        </span>
                    </CardTitle>
                    <CardDescription>
                        Open one to see what the system proposes putting back into it, and why.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="animate-pulse space-y-2">
                            <div className="h-10 rounded bg-muted" />
                            <div className="h-10 rounded bg-muted" />
                        </div>
                    ) : isError ? (
                        <p className="py-8 text-center text-destructive">
                            Could not load the queue.
                        </p>
                    ) : cores.length === 0 ? (
                        <p className="py-8 text-center text-muted-foreground">
                            Nothing waiting. Cores are released into rebuild from their
                            teardown work order.
                        </p>
                    ) : (
                        <div className="w-full overflow-x-auto rounded-md border">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Core</TableHead>
                                        <TableHead>Type</TableHead>
                                        <TableHead>Customer</TableHead>
                                        <TableHead>Fulfilment</TableHead>
                                        <TableHead>Components</TableHead>
                                        <TableHead>Torn down</TableHead>
                                        <TableHead />
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {cores.map((core) => {
                                        const id = String(core.id);
                                        const usable = core.usable_component_count ?? 0;
                                        const harvested = core.harvested_component_count ?? 0;
                                        return (
                                            <TableRow key={id}>
                                                <TableCell className="font-mono text-sm font-medium">
                                                    {core.core_number}
                                                    {(core.rebuild_decisions_open ?? 0) > 0 ? (
                                                        <Badge variant="outline" className="ml-2 font-sans">
                                                            {core.rebuild_decisions_open} slot{core.rebuild_decisions_open === 1 ? "" : "s"} to decide
                                                        </Badge>
                                                    ) : core.rebuild_decisions_open === 0 ? (
                                                        <span className="ml-2 font-sans text-xs text-muted-foreground">planned</span>
                                                    ) : null}
                                                    {(core.pending_finding_count ?? 0) > 0 && (
                                                        // Held at its check until a lead decides.
                                                        <Link to="/reman/cores/$id/rebuild" params={{ id }} className="ml-2">
                                                            <Badge variant="outline" className="border-amber-500/60 font-sans text-amber-700 dark:text-amber-400">
                                                                {core.pending_finding_count} finding{core.pending_finding_count === 1 ? "" : "s"} to decide
                                                            </Badge>
                                                        </Link>
                                                    )}
                                                </TableCell>
                                                <TableCell>{core.core_type_name || "—"}</TableCell>
                                                <TableCell>{core.customer_name || "—"}</TableCell>
                                                <TableCell>
                                                    {core.fulfilment_mode === "REPAIR_RETURN" ? (
                                                        <Badge variant="outline">Returns</Badge>
                                                    ) : (
                                                        <span className="text-muted-foreground">
                                                            Exchange
                                                        </span>
                                                    )}
                                                </TableCell>
                                                <TableCell className="tabular-nums">
                                                    {harvested === 0 ? "—" : `${usable} / ${harvested}`}
                                                </TableCell>
                                                <TableCell>
                                                    {core.disassembly_completed_at
                                                        ? format(
                                                              new Date(core.disassembly_completed_at),
                                                              "MMM d, yyyy",
                                                          )
                                                        : "—"}
                                                </TableCell>
                                                <TableCell className="text-right">
                                                    <Button size="sm" variant="outline" asChild>
                                                        <Link to="/reman/cores/$id/rebuild" params={{ id }}>
                                                            <Wrench className="mr-1 h-4 w-4" />
                                                            Plan rebuild
                                                        </Link>
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })}
                                </TableBody>
                            </Table>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
