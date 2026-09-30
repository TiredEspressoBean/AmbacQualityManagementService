/**
 * The teardown BOM on the part type form: which components a core of this type is
 * expected to yield when disassembled, how many, and how many are usually scrap.
 * Lines are versioned on the backend; each change saves at once.
 */
import { useMemo, useState } from "react";
import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";
import { getCookie } from "@/lib/utils";
import { matchKey } from "@/lib/query-filters";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { toastApiError, useAllows } from "@/pages/scheduling/setup/shared";

type S = components["schemas"];
type Line = S["DisassemblyBOMLine"];

const KEY = "disassembly-bom-lines";
const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") });

/** "0.10" → "10" (percent, as typed); blank stays blank. */
const toPercent = (rate: string | undefined) =>
    rate == null || rate === "" ? "" : String(Math.round(Number(rate) * 1000) / 10);

const linesOptions = (coreType: string) =>
    queryOptions({
        queryKey: [KEY, coreType] as const,
        queryFn: () => api.api_DisassemblyBOMLines_list({
            queries: { core_type: coreType, ordering: "line_number", limit: 200 },
        }) as Promise<S["PaginatedDisassemblyBOMLineList"]>,
    });

function useLineMutations(coreType: string) {
    const qc = useQueryClient();
    const invalidate = () => qc.invalidateQueries(matchKey(linesOptions(coreType).queryKey));
    return {
        create: useMutation({
            mutationFn: (data: S["DisassemblyBOMLineRequest"]) =>
                api.api_DisassemblyBOMLines_create(data, { headers: csrf() }),
            onSuccess: invalidate,
        }),
        update: useMutation({
            mutationFn: ({ id, data }: { id: string; data: S["PatchedDisassemblyBOMLineRequest"] }) =>
                api.api_DisassemblyBOMLines_partial_update(data, { params: { id }, headers: csrf() }),
            onSuccess: invalidate,
        }),
        remove: useMutation({
            mutationFn: (id: string) =>
                api.api_DisassemblyBOMLines_destroy(undefined, { params: { id }, headers: csrf() }),
            onSuccess: invalidate,
        }),
    };
}

function NumberCell({ value, label, disabled, onCommit }: {
    value: string; label: string; disabled: boolean; onCommit: (v: string) => void;
}) {
    const [draft, setDraft] = useState(value);
    if (disabled) return <span className="tabular-nums">{value || "—"}</span>;
    return (
        <Input type="number" min={0} step="any" inputMode="decimal" className="h-8 w-20" aria-label={label}
            value={draft} onChange={(e) => setDraft(e.target.value)}
            onBlur={() => { if (draft !== value) onCommit(draft); }} />
    );
}

export function DisassemblyBomPanel({ partTypeId }: { partTypeId: string }) {
    const allows = useAllows();
    const canAdd = allows("add_disassemblybomline");
    const canChange = allows("change_disassemblybomline");
    const canDelete = allows("delete_disassemblybomline");

    const { data, isLoading } = useQuery(linesOptions(partTypeId));
    const lines = useMemo<Line[]>(() => data?.results ?? [], [data]);
    const { data: typesPage } = useRetrievePartTypes({ limit: 500 });
    const { create, update, remove } = useLineMutations(partTypeId);

    const available = useMemo(() => {
        const taken = new Set(lines.map((l) => l.component_type));
        return (typesPage?.results ?? []).filter((t) => t.id !== partTypeId && !taken.has(t.id));
    }, [typesPage, lines, partTypeId]);

    const [component, setComponent] = useState("");
    const [qty, setQty] = useState("1");
    const [fallout, setFallout] = useState("");

    function add() {
        if (!component) return;
        const q = Number(qty);
        const f = fallout.trim() === "" ? 0 : Number(fallout);
        if (!Number.isInteger(q) || q < 1) return toastApiError(new Error("Quantity must be a whole number, 1 or more"));
        if (!Number.isFinite(f) || f < 0 || f > 100) return toastApiError(new Error("Fallout must be a percentage from 0 to 100"));
        create.mutate(
            {
                core_type: partTypeId, component_type: component, expected_qty: q,
                expected_fallout_rate: String(f / 100),
                line_number: (Math.max(0, ...lines.map((l) => l.line_number ?? 0)) || 0) + 1,
            },
            {
                onSuccess: () => { setComponent(""); setQty("1"); setFallout(""); },
                onError: (e) => toastApiError(e, ["component_type", "expected_qty", "expected_fallout_rate", "non_field_errors"]),
            },
        );
    }

    function commitQty(line: Line, raw: string) {
        const q = Number(raw);
        if (!Number.isInteger(q) || q < 1) return toastApiError(new Error("Quantity must be a whole number, 1 or more"));
        update.mutate({ id: line.id, data: { expected_qty: q } }, { onError: (e) => toastApiError(e) });
    }

    function commitFallout(line: Line, raw: string) {
        const f = raw.trim() === "" ? 0 : Number(raw);
        if (!Number.isFinite(f) || f < 0 || f > 100) return toastApiError(new Error("Fallout must be a percentage from 0 to 100"));
        update.mutate({ id: line.id, data: { expected_fallout_rate: String(f / 100) } }, { onError: (e) => toastApiError(e) });
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-lg">Teardown</CardTitle>
                <CardDescription>
                    For a core of this type: the components disassembly is expected to yield, and
                    the share usually scrapped. Leave empty for part types that aren't cores.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {isLoading ? (
                    <p className="text-sm text-muted-foreground">Loading…</p>
                ) : lines.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No teardown components listed.</p>
                ) : (
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Component</TableHead>
                                <TableHead className="w-28">Per core</TableHead>
                                <TableHead className="w-28">Fallout %</TableHead>
                                <TableHead className="w-28">Usable</TableHead>
                                {canDelete && <TableHead className="w-12"><span className="sr-only">Remove</span></TableHead>}
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {lines.map((l) => (
                                <TableRow key={`${l.id}-${l.version}`}>
                                    <TableCell className="font-medium">{l.component_type_name}</TableCell>
                                    <TableCell>
                                        <NumberCell value={String(l.expected_qty ?? 1)} label={`${l.component_type_name} per core`}
                                            disabled={!canChange} onCommit={(v) => commitQty(l, v)} />
                                    </TableCell>
                                    <TableCell>
                                        <NumberCell value={toPercent(l.expected_fallout_rate)} label={`${l.component_type_name} fallout percent`}
                                            disabled={!canChange} onCommit={(v) => commitFallout(l, v)} />
                                    </TableCell>
                                    <TableCell className="tabular-nums text-muted-foreground">{l.expected_usable_qty}</TableCell>
                                    {canDelete && (
                                        <TableCell className="text-right">
                                            <Button variant="ghost" size="icon" className="text-destructive"
                                                aria-label={`Remove ${l.component_type_name}`}
                                                onClick={() => {
                                                    if (window.confirm(`Remove ${l.component_type_name} from the teardown?`)) {
                                                        remove.mutate(l.id, { onError: (e) => toastApiError(e) });
                                                    }
                                                }}>
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    )}
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}

                {canAdd && (
                    <div className="grid gap-3 border-t pt-4 sm:grid-cols-[minmax(0,1fr)_6rem_6rem_auto] sm:items-end">
                        <div className="space-y-1.5">
                            <Label>Add a component</Label>
                            <Select value={component} onValueChange={(v) => v && setComponent(v)}>
                                <SelectTrigger aria-label="Component part type"><SelectValue placeholder="Select a part type" /></SelectTrigger>
                                <SelectContent>
                                    {available.map((t) => (
                                        <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor={`td-qty-${partTypeId}`}>Per core</Label>
                            <Input id={`td-qty-${partTypeId}`} type="number" min={1} step={1} value={qty}
                                onChange={(e) => setQty(e.target.value)} />
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor={`td-fall-${partTypeId}`}>Fallout %</Label>
                            <Input id={`td-fall-${partTypeId}`} type="number" min={0} max={100} step="any" placeholder="0"
                                value={fallout} onChange={(e) => setFallout(e.target.value)} />
                        </div>
                        <Button size="sm" className="h-9" onClick={add} disabled={!component || create.isPending}>
                            <Plus className="mr-1 h-4 w-4" /> Add
                        </Button>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
