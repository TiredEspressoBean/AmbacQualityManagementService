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
 * Cores torn down and waiting on a rebuild decision.
 *
 * Exists so the loop is a queue somebody works rather than a URL you have to know.
 * DISASSEMBLED is the whole filter: a core is ready when teardown is finished, and
 * "grading complete" is implied by it — components are graded as they are captured.
 */
export function RebuildQueuePage() {
    const { data, isLoading, isError } = useRetrieveCores({
        status: "DISASSEMBLED",
        ordering: "disassembly_completed_at",
        limit: 100,
    });

    const cores = data?.results ?? [];

    return (
        <div className="max-w-6xl mx-auto py-10 space-y-6">
            <div>
                <h1 className="text-2xl font-bold">Ready to rebuild</h1>
                <p className="text-muted-foreground">
                    Cores that finished teardown and have no rebuild decision yet. Oldest
                    first — a core sitting here is capital on a shelf.
                </p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-baseline gap-3">
                        <span>Queue</span>
                        <span className="text-sm font-normal text-muted-foreground tabular-nums">
                            {cores.length}
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
                            Nothing waiting — every torn-down core has been dealt with.
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
