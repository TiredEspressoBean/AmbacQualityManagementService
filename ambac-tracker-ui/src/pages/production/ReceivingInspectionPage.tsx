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
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { Schema } from "@/lib/api/types";
import {
    useSamplePlan, useOpenInspection, useRecordUnits, useRecordBulk, useAcceptLot, useRejectLot, useRaiseScar,
} from "@/hooks/useReceivingMutations";
import { useSupplierQualificationStatus } from "@/hooks/useSupplierQualifications";
import { EntityDocumentsEditor } from "@/components/documents/EntityDocumentsEditor";
import { RejectDispositionDialog, type RejectDispositionValues } from "@/components/reject-disposition-dialog";
import { getCookie } from "@/lib/utils";
import { FileText } from "lucide-react";

type Char = NonNullable<Schema<"SamplePlanResponse">["characteristics"]>[number];

/** Warns when the lot's supplier isn't qualified for its part type. */
function QualificationBanner({ supplierId, partTypeId }: { supplierId?: string | null; partTypeId?: string | null }) {
    const { data: q } = useSupplierQualificationStatus(supplierId ?? undefined, partTypeId ?? undefined);
    if (!supplierId || !q || q.qualified) return null;
    return (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
            ⚠ This lot's supplier is <b>not qualified</b> for this part type. If the part type requires
            qualification, the lot was held — qualify the supplier (Approved Suppliers) before accepting.
        </div>
    );
}

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

    // Z1.9 variables plan: measures one characteristic, accepts on x̄/s vs k (no Ac/Re).
    const isVariables = samplePlan?.method === "K_SINGLE" || samplePlan?.k != null;
    const varChar = isVariables
        ? characteristics.find((c) => String(c.id) === String(samplePlan?.variables_characteristic_id))
        : undefined;

    // Industry-standard receiving default = attribute "count defectives" over the
    // sample (matches C=0 / Z1.4). Variables always measures per unit; otherwise switch
    // to per-unit capture only when the plan has numeric characteristics. User can override.
    const [modeOverride, setModeOverride] = useState<"unit" | "bulk" | null>(null);
    const hasNumericChar = characteristics.some((c) => c.type === "NUMERIC");
    const mode: "unit" | "bulk" = isVariables ? "unit" : (modeOverride ?? (hasNumericChar ? "unit" : "bulk"));
    const [bulkDefectives, setBulkDefectives] = useState("0");
    const [docsOpen, setDocsOpen] = useState(false);
    const [rejectOpen, setRejectOpen] = useState(false);
    const [rejectSubmitting, setRejectSubmitting] = useState(false);
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

    // Z1.9 variables verdict — advisory; the backend evaluate_lot_acceptance is
    // authoritative when measurements are recorded. Computes x̄/s and the quality
    // index against k from the variables characteristic's tolerances.
    const variablesVerdict = useMemo(() => {
        if (!isVariables || !varChar || samplePlan?.k == null) return null;
        const vals = units.map((u) => parseFloat(cells[`${u}:${varChar.id}`])).filter((v) => !Number.isNaN(v));
        if (vals.length < Math.max(n, 2)) return { state: "progress" as const, recorded: vals.length };
        const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
        const s = Math.sqrt(vals.reduce((a, b) => a + (b - mean) ** 2, 0) / (vals.length - 1));
        const usl = varChar.nominal != null && varChar.upper_tol != null ? varChar.nominal + varChar.upper_tol : null;
        const lsl = varChar.nominal != null && varChar.lower_tol != null ? varChar.nominal - varChar.lower_tol : null;
        const k = samplePlan.k as number;
        const qu = usl != null && s > 0 ? (usl - mean) / s : null;
        const ql = lsl != null && s > 0 ? (mean - lsl) / s : null;
        const idx = [qu, ql].filter((q): q is number => q != null);
        const accept = s === 0
            ? (usl == null || mean <= usl) && (lsl == null || mean >= lsl)
            : idx.length > 0 && idx.every((q) => q >= k);
        return { state: accept ? ("accept" as const) : ("reject" as const), mean, s, qu, ql, k, recorded: vals.length };
    }, [isVariables, varChar, samplePlan, units, cells, n]);

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

    // Reject = open a nonconformance, not just a status flip. Reject the lot, then
    // open a QuarantineDisposition linked to the lot's inspection report (which
    // carries material_lot); optionally raise a SCAR for return-to-supplier. The
    // direct QuarantineDisposition.material_lot FK is the small backend follow-up
    // (design §10.7) — today we link via the report so the flow is real end-to-end.
    async function confirmReject(values: RejectDispositionValues) {
        if (!lot) return;
        setRejectSubmitting(true);
        let dispositionOk = true;
        try {
            const qr = (await rejectMut.mutateAsync({ id: lotId })) as { id?: string } | undefined;
            try {
                await api.api_QuarantineDispositions_create(
                    {
                        current_state: "OPEN",
                        disposition_type: values.disposition_type,
                        severity: values.severity,
                        description: values.description,
                        part: null,
                        quality_reports: qr?.id ? [qr.id] : [],
                    } as never,
                    { headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" } },
                );
            } catch {
                dispositionOk = false;
            }
            if (values.raise_scar && lot.supplier) {
                try { await scarMut.mutateAsync({ id: lotId }); } catch { /* non-fatal */ }
            }
            toast.success(dispositionOk ? "Lot rejected · disposition opened" : "Lot rejected (open the disposition manually)");
            navigate({ to: "/production/material-lots" });
        } catch {
            toast.error("Could not reject lot");
        } finally {
            setRejectSubmitting(false);
            setRejectOpen(false);
        }
    }

    return (
        <div className="max-w-4xl mx-auto space-y-4">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-3">
                        <span className="font-mono">{lot.lot_number}</span>
                        <Badge variant="outline">{lot.status}</Badge>
                        <Button variant="outline" size="sm" className="ml-auto" onClick={() => setDocsOpen(true)}>
                            <FileText className="h-4 w-4 mr-1" /> Documents (CoC, certs)
                        </Button>
                    </CardTitle>
                    <p className="text-sm text-muted-foreground">
                        {lot.material_type_name ?? lot.material_description ?? "—"} · {lot.supplier_name ?? "no supplier"} · qty {lot.quantity}
                    </p>
                </CardHeader>
                <CardContent className="space-y-3">
                    <QualificationBanner supplierId={lot.supplier as string | null} partTypeId={lot.material_type as string | null} />
                    {noPlan && (
                        <p className="text-sm text-destructive">
                            No RECEIVING step configured for this part type. Add a Receiving Inspection step to its
                            process (and a sampling ruleset) first.
                        </p>
                    )}
                    {samplePlan && (
                        <div className="rounded-md border p-3 text-sm">
                            <div className="font-medium">
                                Sample plan ({samplePlan.strategy}, level {samplePlan.inspection_level}{samplePlan.severity ? `, ${samplePlan.severity}` : ""})
                            </div>
                            <div className="text-muted-foreground">
                                {isVariables ? (
                                    <>Inspect <b>{n}</b> of {lot.quantity} · measure <b>{varChar?.label ?? "characteristic"}</b> · accept if x̄/s index ≥ k = <b>{samplePlan.k}</b></>
                                ) : (
                                    <>Inspect <b>{n}</b> of {lot.quantity} · Accept ≤ <b>{ac}</b> · Reject ≥ <b>{re}</b></>
                                )}
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
                            {!isVariables && (
                                <div className="flex gap-1">
                                    <Button size="sm" variant={mode === "bulk" ? "default" : "outline"}
                                        onClick={() => setModeOverride("bulk")}>Count defectives</Button>
                                    <Button size="sm" variant={mode === "unit" ? "default" : "outline"}
                                        onClick={() => setModeOverride("unit")} disabled={characteristics.length === 0}>Measure each unit</Button>
                                </div>
                            )}

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
                                    {isVariables ? (
                                        <TooltipProvider>
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <div className="inline-flex items-center gap-2 text-sm font-medium cursor-default">
                                                        Variables verdict:
                                                        {variablesVerdict?.state === "accept" ? (
                                                            <Badge className="bg-green-600 hover:bg-green-600">ACCEPT</Badge>
                                                        ) : variablesVerdict?.state === "reject" ? (
                                                            <Badge variant="destructive">REJECT</Badge>
                                                        ) : (
                                                            <span className="text-muted-foreground">{variablesVerdict?.recorded ?? 0}/{n} readings</span>
                                                        )}
                                                    </div>
                                                </TooltipTrigger>
                                                <TooltipContent>
                                                    {variablesVerdict && variablesVerdict.state !== "progress" ? (
                                                        <div className="text-xs space-y-0.5">
                                                            <div>x̄ = {variablesVerdict.mean.toFixed(4)} · s = {variablesVerdict.s.toFixed(4)}</div>
                                                            {variablesVerdict.qu != null && <div>QU = (USL−x̄)/s = {variablesVerdict.qu.toFixed(3)}</div>}
                                                            {variablesVerdict.ql != null && <div>QL = (x̄−LSL)/s = {variablesVerdict.ql.toFixed(3)}</div>}
                                                            <div>k = {variablesVerdict.k.toFixed(3)} · accept if index ≥ k</div>
                                                        </div>
                                                    ) : (
                                                        <div className="text-xs">Enter all {n} sampled readings of {varChar?.label} to compute the verdict.</div>
                                                    )}
                                                </TooltipContent>
                                            </Tooltip>
                                        </TooltipProvider>
                                    ) : (
                                        <div className={`text-sm font-medium ${verdict === "reject" ? "text-destructive" : verdict === "accept" ? "text-green-600" : "text-muted-foreground"}`}>
                                            Defectives: {defectives} / Accept ≤ {ac} / Reject ≥ {re}
                                            {verdict === "reject" && " — will REJECT"}
                                            {verdict === "accept" && " — will ACCEPT"}
                                            {verdict === "progress" && ` — ${unitsComplete}/${n} units inspected`}
                                        </div>
                                    )}
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
                                        onSuccess: () => { toast.success("Lot accepted"); navigate({ to: "/production/material-lots" }); },
                                        onError: () => toast.error("Could not accept lot"),
                                    })}>
                                    Accept
                                </Button>
                                <Button variant="destructive" disabled={rejectMut.isPending || rejectSubmitting}
                                    onClick={() => setRejectOpen(true)}>
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
            <EntityDocumentsEditor
                contentTypeModel="materiallot"
                objectId={String(lot.id)}
                label={lot.lot_number}
                description="Certificate of Conformance, mill/material certs, packing slips, and supplier documents for this lot."
                open={docsOpen}
                onOpenChange={setDocsOpen}
            />
            <RejectDispositionDialog
                open={rejectOpen}
                onOpenChange={setRejectOpen}
                lotNumber={lot.lot_number ?? String(lot.id)}
                supplierName={lot.supplier_name}
                hasSupplier={!!lot.supplier}
                quantity={lot.quantity ?? 0}
                defectives={mode === "bulk" ? (parseInt(bulkDefectives) || 0) : defectives}
                sampleSize={n}
                acceptNumber={ac}
                submitting={rejectSubmitting}
                onConfirm={confirmReject}
            />
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
