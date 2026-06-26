import { useMemo, useState } from "react";
import { useParams, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Schema } from "@/lib/api/types";
import {
    useSamplePlan, useOpenInspection, useRecordUnits, useRecordBulk, useAcceptLot, useRejectLot, useRaiseScar,
} from "@/hooks/useReceivingMutations";

type Char = NonNullable<Schema<"SamplePlanResponse">["characteristics"]>[number];

/** null = not yet entered; true/false = within / out of spec. */
function cellInSpec(c: Char, raw: string | undefined): boolean | null {
    if (raw === undefined || raw === "") return null;
    if (c.type === "PASS_FAIL") return raw === "PASS";
    const v = parseFloat(raw);
    if (Number.isNaN(v)) return null;
    if (c.nominal == null || c.upper_tol == null || c.lower_tol == null) return true; // no tolerance to judge against
    return v >= c.nominal - c.lower_tol && v <= c.nominal + c.upper_tol;
}

export function ReceivingInspectionPage() {
    const { lotId } = useParams({ strict: false }) as { lotId: string };
    const navigate = useNavigate();

    const lotQuery = useQuery({
        queryKey: ["material-lot", lotId],
        queryFn: () => api.api_MaterialLots_retrieve({ params: { id: lotId } } as never) as Promise<Schema<"MaterialLot">>,
    });
    const lot = lotQuery.data;

    const { data: samplePlan, isError: noPlan } = useSamplePlan(lotId);
    const characteristics = (samplePlan?.characteristics ?? []) as Char[];
    const n = samplePlan?.sample_size ?? 0;
    const ac = samplePlan?.accept_number ?? 0;
    const re = samplePlan?.reject_number ?? 1;

    const [mode, setMode] = useState<"unit" | "bulk">("unit");
    const [bulkDefectives, setBulkDefectives] = useState("0");
    // cells keyed `${unit}:${charId}`
    const [cells, setCells] = useState<Record<string, string>>({});
    const setCell = (unit: number, charId: string, v: string) =>
        setCells((prev) => ({ ...prev, [`${unit}:${charId}`]: v }));

    const openMut = useOpenInspection();
    const recordMut = useRecordUnits();
    const recordBulkMut = useRecordBulk();
    const acceptMut = useAcceptLot();
    const rejectMut = useRejectLot();
    const scarMut = useRaiseScar();

    const units = useMemo(() => Array.from({ length: n }, (_, i) => i + 1), [n]);

    const unitDefective = (u: number) =>
        characteristics.some((c) => cellInSpec(c, cells[`${u}:${c.id}`]) === false);
    const unitComplete = (u: number) =>
        characteristics.length > 0 && characteristics.every((c) => cellInSpec(c, cells[`${u}:${c.id}`]) !== null);

    const defectives = units.filter(unitDefective).length;
    const unitsComplete = units.filter(unitComplete).length;
    const verdict: "reject" | "accept" | "progress" =
        defectives >= re ? "reject" : unitsComplete >= n && defectives <= ac ? "accept" : "progress";

    if (lotQuery.isLoading) return <div className="p-6">Loading…</div>;
    if (!lot) return <div className="p-6">Lot not found.</div>;

    function buildUnitsPayload() {
        return units
            .map((u) => ({
                sample_number: u,
                measurements: characteristics
                    .map((c) => {
                        const raw = cells[`${u}:${c.id}`];
                        if (raw === undefined || raw === "") return null;
                        return c.type === "PASS_FAIL"
                            ? { definition: String(c.id), value_pass_fail: raw as "PASS" | "FAIL" }
                            : { definition: String(c.id), value_numeric: parseFloat(raw) };
                    })
                    .filter(Boolean) as { definition: string; value_numeric?: number; value_pass_fail?: "PASS" | "FAIL" }[],
            }))
            .filter((u) => u.measurements.length > 0);
    }

    return (
        <div className="max-w-4xl mx-auto space-y-4">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-3">
                        <span className="font-mono">{lot.lot_number}</span>
                        <Badge variant="outline">{lot.status}</Badge>
                    </CardTitle>
                    <p className="text-sm text-muted-foreground">
                        {lot.material_type_name ?? lot.material_description ?? "—"} · {lot.supplier_name ?? "no supplier"} · qty {lot.quantity}
                    </p>
                </CardHeader>
                <CardContent className="space-y-3">
                    {noPlan && (
                        <p className="text-sm text-destructive">
                            No RECEIVING step configured for this part type. Add a Receiving Inspection step to its
                            process (and a sampling ruleset) first.
                        </p>
                    )}
                    {samplePlan && (
                        <div className="rounded-md border p-3 text-sm">
                            <div className="font-medium">Sample plan ({samplePlan.strategy}, level {samplePlan.inspection_level}, {samplePlan.severity})</div>
                            <div className="text-muted-foreground">
                                Inspect <b>{n}</b> of {lot.quantity} · Accept ≤ <b>{ac}</b> · Reject ≥ <b>{re}</b>
                            </div>
                        </div>
                    )}

                    {lot.status === "RECEIVED" && (
                        <Button disabled={noPlan || openMut.isPending}
                            onClick={() => openMut.mutate({ id: lotId }, {
                                onSuccess: () => { toast.success("Inspection opened"); lotQuery.refetch(); },
                                onError: () => toast.error("Could not open inspection"),
                            })}>
                            {openMut.isPending ? "Opening…" : "Open Inspection"}
                        </Button>
                    )}

                    {lot.status === "AWAITING_INSPECTION" && samplePlan?.has_substeps && (
                        <DwiLaunch samplePlan={samplePlan} lotId={lotId} navigate={navigate} />
                    )}

                    {lot.status === "AWAITING_INSPECTION" && !samplePlan?.has_substeps && (
                        <div className="space-y-3">
                            <div className="flex gap-1">
                                <Button size="sm" variant={mode === "unit" ? "default" : "outline"}
                                    onClick={() => setMode("unit")} disabled={characteristics.length === 0}>Per unit</Button>
                                <Button size="sm" variant={mode === "bulk" ? "default" : "outline"}
                                    onClick={() => setMode("bulk")}>Bulk</Button>
                            </div>

                            {mode === "unit" && characteristics.length === 0 && (
                                <p className="text-sm text-muted-foreground">No characteristics on the receiving step — use Bulk, or accept/reject below.</p>
                            )}

                            {mode === "unit" && characteristics.length > 0 && (
                                <>
                                    <div className="overflow-x-auto">
                                        <Table>
                                            <TableHeader>
                                                <TableRow>
                                                    <TableHead className="w-16">Unit</TableHead>
                                                    {characteristics.map((c) => (
                                                        <TableHead key={c.id}>
                                                            {c.label}
                                                            {c.type === "NUMERIC" && c.nominal != null && (
                                                                <span className="ml-1 text-xs font-normal text-muted-foreground">
                                                                    {c.nominal}
                                                                    {c.upper_tol != null && ` +${c.upper_tol}`}
                                                                    {c.lower_tol != null && ` −${c.lower_tol}`}
                                                                    {c.unit ? ` ${c.unit}` : ""}
                                                                </span>
                                                            )}
                                                        </TableHead>
                                                    ))}
                                                    <TableHead className="w-20">Unit</TableHead>
                                                </TableRow>
                                            </TableHeader>
                                            <TableBody>
                                                {units.map((u) => {
                                                    const def = unitDefective(u);
                                                    return (
                                                        <TableRow key={u} className={def ? "bg-destructive/10" : ""}>
                                                            <TableCell className="font-medium tabular-nums">{u}</TableCell>
                                                            {characteristics.map((c) => {
                                                                const key = `${u}:${c.id}`;
                                                                const spec = cellInSpec(c, cells[key]);
                                                                const bad = spec === false;
                                                                return (
                                                                    <TableCell key={c.id}>
                                                                        {c.type === "PASS_FAIL" ? (
                                                                            <Select value={cells[key] ?? ""} onValueChange={(v) => setCell(u, String(c.id), v)}>
                                                                                <SelectTrigger className={`w-24 ${bad ? "border-destructive text-destructive" : ""}`}><SelectValue placeholder="—" /></SelectTrigger>
                                                                                <SelectContent>
                                                                                    <SelectItem value="PASS">Pass</SelectItem>
                                                                                    <SelectItem value="FAIL">Fail</SelectItem>
                                                                                </SelectContent>
                                                                            </Select>
                                                                        ) : (
                                                                            <Input className={`w-28 ${bad ? "border-destructive text-destructive" : ""}`}
                                                                                value={cells[key] ?? ""} placeholder={c.unit || "value"}
                                                                                onChange={(e) => setCell(u, String(c.id), e.target.value)} />
                                                                        )}
                                                                    </TableCell>
                                                                );
                                                            })}
                                                            <TableCell>
                                                                {def ? <Badge variant="destructive">defect</Badge>
                                                                    : unitComplete(u) ? <Badge variant="outline" className="text-green-600 border-green-600">ok</Badge>
                                                                        : <span className="text-xs text-muted-foreground">—</span>}
                                                            </TableCell>
                                                        </TableRow>
                                                    );
                                                })}
                                            </TableBody>
                                        </Table>
                                    </div>
                                    <div className={`text-sm font-medium ${verdict === "reject" ? "text-destructive" : verdict === "accept" ? "text-green-600" : "text-muted-foreground"}`}>
                                        Defectives: {defectives} / Accept ≤ {ac} / Reject ≥ {re}
                                        {verdict === "reject" && " — will REJECT"}
                                        {verdict === "accept" && " — will ACCEPT"}
                                        {verdict === "progress" && ` — ${unitsComplete}/${n} units inspected`}
                                    </div>
                                    <Button variant="outline" disabled={recordMut.isPending}
                                        onClick={() => recordMut.mutate({ id: lotId, units: buildUnitsPayload() }, {
                                            onSuccess: () => { toast.success("Measurements recorded"); lotQuery.refetch(); },
                                            onError: () => toast.error("Could not record measurements"),
                                        })}>
                                        Record Measurements
                                    </Button>
                                </>
                            )}

                            {mode === "bulk" && (() => {
                                const bd = parseInt(bulkDefectives) || 0;
                                const v = bd >= re ? "reject" : bd <= ac ? "accept" : "progress";
                                return (
                                    <div className="space-y-2">
                                        <p className="text-sm text-muted-foreground">
                                            Inspect the sample of {n} and record the number of defectives found.
                                        </p>
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm">Defectives found</span>
                                            <Input className="w-24" type="number" min={0} value={bulkDefectives}
                                                onChange={(e) => setBulkDefectives(e.target.value)} />
                                            <span className="text-sm text-muted-foreground">of {n} inspected</span>
                                        </div>
                                        <div className={`text-sm font-medium ${v === "reject" ? "text-destructive" : v === "accept" ? "text-green-600" : "text-muted-foreground"}`}>
                                            Defectives: {bd} / Accept ≤ {ac} / Reject ≥ {re}
                                            {v === "reject" && " — will REJECT"}
                                            {v === "accept" && " — will ACCEPT"}
                                        </div>
                                        <Button variant="outline" disabled={recordBulkMut.isPending}
                                            onClick={() => recordBulkMut.mutate({ id: lotId, defectives_found: bd }, {
                                                onSuccess: () => { toast.success("Result recorded"); lotQuery.refetch(); },
                                                onError: () => toast.error("Could not record result"),
                                            })}>
                                            Record Result
                                        </Button>
                                    </div>
                                );
                            })()}

                            <div className="flex gap-2 border-t pt-3">
                                <Button disabled={acceptMut.isPending}
                                    onClick={() => acceptMut.mutate({ id: lotId }, {
                                        onSuccess: () => { toast.success("Lot accepted"); navigate({ to: "/production/receiving-inspection" }); },
                                        onError: () => toast.error("Could not accept lot"),
                                    })}>
                                    Accept
                                </Button>
                                <Button variant="destructive" disabled={rejectMut.isPending}
                                    onClick={() => rejectMut.mutate({ id: lotId }, {
                                        onSuccess: () => { toast.success("Lot rejected"); navigate({ to: "/production/receiving-inspection" }); },
                                        onError: () => toast.error("Could not reject lot"),
                                    })}>
                                    Reject
                                </Button>
                            </div>
                        </div>
                    )}

                    {(lot.status === "ACCEPTED" || lot.status === "REJECTED") && (
                        <div className="space-y-3">
                            <p className="text-sm">This lot has been <b>{lot.status.toLowerCase()}</b>.</p>
                            {lot.status === "REJECTED" && lot.supplier && (
                                <Button variant="outline" disabled={scarMut.isPending}
                                    onClick={() => scarMut.mutate({ id: lotId }, {
                                        onSuccess: (r: { capa_number?: string }) =>
                                            toast.success(`SCAR raised${r?.capa_number ? ` (${r.capa_number})` : ""}`),
                                        onError: () => toast.error("Could not raise SCAR"),
                                    })}>
                                    Raise SCAR
                                </Button>
                            )}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

function DwiLaunch({ samplePlan, lotId, navigate }: {
    samplePlan: Schema<"SamplePlanResponse">;
    lotId: string;
    navigate: ReturnType<typeof useNavigate>;
}) {
    return (
        <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
                This receiving step has digital work instructions. Run the inspection through the operator runtime.
            </p>
            <Button
                disabled={!samplePlan.step_id || !samplePlan.step_execution_id}
                onClick={() =>
                    navigate({
                        to: "/operator/steps/$stepId/substeps",
                        params: { stepId: String(samplePlan.step_id) },
                        search: { execution: String(samplePlan.step_execution_id), material_lot: lotId, at: 0 } as never,
                    })
                }
            >
                Run Inspection (DWI)
            </Button>
        </div>
    );
}
