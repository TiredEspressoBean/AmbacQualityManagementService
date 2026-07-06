import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getCookie } from "@/lib/utils";
import {
    useSamplePlan, useAcceptLot, useRejectLot, useRecordBulk, useRaiseScar,
} from "@/hooks/useReceivingMutations";
import { RejectDispositionDialog, type RejectDispositionValues } from "@/components/reject-disposition-dialog";

/** A measurement the operator captured in the DWI, flattened for verdict math. */
export type CapturedMeasurement = {
    definition_id: string;
    value_numeric: number | null;
    value_pass_fail: string | null;
};

type Verdict = "accept" | "reject" | "pending";

/**
 * The acceptance decision, rendered as the final stage of a receiving DWI so
 * the inspector never leaves the guided runtime. Family-aware:
 *  - attribute (C=0 / Z1.4): the inspector records defectives found in the
 *    sample → verdict vs Ac/Re.
 *  - variables (Z1.9): verdict computed from the readings captured in-flow
 *    (x̄/s vs k).
 *  - holistic / no plan: pass/fail from the captured measurements.
 *
 * Accept → transitions the lot. Reject → the guided disposition step (reason /
 * qty / RTV+SCAR) right here, then transitions + opens the nonconformance.
 * Reuses the existing receiving services; no new backend.
 */
type ServerVerdict = {
    status: string;
    is_variables: boolean;
    sample_size: number | null;
    accept_number: number | null;
    reject_number: number | null;
    k: number | null;
    defectives: number;
    units_recorded: number;
    readings: number;
};

export function ReceivingAcceptanceStage({
    lotId,
    capturedMeasurements,
    flushCaptures,
    unitMode = false,
}: {
    lotId: string;
    capturedMeasurements: CapturedMeasurement[];
    /** Persist the DWI captures to the QR. Returns false if the flush failed. */
    flushCaptures: () => Promise<boolean>;
    /** Unit-by-unit (Z1.9): the sample's readings are on the server, so the
     *  verdict comes from the evaluate_receiving endpoint, not client memory. */
    unitMode?: boolean;
}) {
    const navigate = useNavigate();

    const lotQuery = useQuery({
        queryKey: ["material-lot", lotId],
        queryFn: () => api.api_MaterialLots_retrieve({ params: { id: lotId } } as never) as Promise<Schema<"MaterialLot">>,
    });
    const lot = lotQuery.data;

    const { data: samplePlan } = useSamplePlan(lotId);
    const characteristics = samplePlan?.characteristics ?? [];
    const n = samplePlan?.sample_size ?? 0;
    const ac = samplePlan?.accept_number ?? 0;
    const re = samplePlan?.reject_number ?? 1;
    const isVariables = samplePlan?.method === "K_SINGLE" || samplePlan?.k != null;
    const varChar = isVariables
        ? characteristics.find((c) => String(c.id) === String(samplePlan?.variables_characteristic_id))
        : undefined;

    // Bulk (attribute): defects tallied by RIP characteristic (the "type"),
    // summed for the Ac/Re decision (the "amount"). Falls back to a single
    // total when the plan defines no characteristics.
    const [defectByChar, setDefectByChar] = useState<Record<string, string>>({});
    const [defectTotal, setDefectTotal] = useState("0");
    const [rejectOpen, setRejectOpen] = useState(false);
    const [busy, setBusy] = useState(false);
    const [flushed, setFlushed] = useState(false);
    const [evaluating, setEvaluating] = useState(false);
    const [serverVerdict, setServerVerdict] = useState<ServerVerdict | null>(null);

    const acceptMut = useAcceptLot();
    const rejectMut = useRejectLot();
    const recordBulkMut = useRecordBulk();
    const scarMut = useRaiseScar();

    // Persist the DWI captures exactly once — _handle_measurement isn't
    // idempotent (each submit creates a new MeasurementResult), so a second
    // flush would duplicate this unit's readings.
    async function ensureFlushed(): Promise<boolean> {
        if (flushed) return true;
        const ok = await flushCaptures();
        if (ok) setFlushed(true);
        return ok;
    }

    // Unit-by-unit: flush the final reading, then ask the server for the
    // family-correct verdict over all recorded units (attribute defective-unit
    // count / Z1.9 x̄·s vs k).
    async function evaluateOnServer() {
        setEvaluating(true);
        try {
            if (!(await ensureFlushed())) { toast.error("Could not save the reading"); return; }
            const res = await fetch(`/api/MaterialLots/${lotId}/evaluate_receiving/`, { credentials: "include" });
            if (!res.ok) { toast.error("Could not evaluate the lot"); return; }
            setServerVerdict(await res.json());
        } catch {
            toast.error("Could not evaluate the lot");
        } finally {
            setEvaluating(false);
        }
    }

    // Z1.9 verdict from the readings the operator captured for the measured
    // characteristic (x̄/s vs k). Mirrors the receiving page's advisory logic.
    const variablesVerdict = useMemo(() => {
        if (!isVariables || !varChar || samplePlan?.k == null) return null;
        const vals = capturedMeasurements
            .filter((m) => String(m.definition_id) === String(varChar.id) && m.value_numeric != null)
            .map((m) => m.value_numeric as number);
        if (vals.length < Math.max(n, 2)) return { state: "pending" as Verdict, recorded: vals.length };
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
        return { state: (accept ? "accept" : "reject") as Verdict, mean, s, qu, ql, k, recorded: vals.length };
    }, [isVariables, varChar, samplePlan, capturedMeasurements, n]);

    // Attribute (bulk): tally defects by RIP characteristic when the plan has
    // them, else a single total. The sum is the defect "amount" checked vs Ac/Re.
    const hasPlan = n > 0;
    const useByChar = !isVariables && hasPlan && characteristics.length > 0;
    const bd = useByChar
        ? characteristics.reduce((sum, c) => sum + (parseInt(defectByChar[String(c.id)]) || 0), 0)
        : (parseInt(defectTotal) || 0);
    const defectBreakdown = useByChar
        ? characteristics
            .filter((c) => (parseInt(defectByChar[String(c.id)]) || 0) > 0)
            .map((c) => `${c.label}: ${parseInt(defectByChar[String(c.id)]) || 0}`)
            .join(", ")
        : "";
    const attributeVerdict: Verdict = bd >= re ? "reject" : bd <= ac ? "accept" : "pending";

    const verdict: Verdict = unitMode
        // Unit-by-unit: the server owns the verdict (all units live in the DB).
        ? (serverVerdict
            ? (serverVerdict.status === "PASS" ? "accept" : serverVerdict.status === "FAIL" ? "reject" : "pending")
            : "pending")
        : isVariables
            ? (variablesVerdict?.state ?? "pending")
            : hasPlan
                ? attributeVerdict
                // Holistic (no sampling plan): fall out of the captured measurements.
                : capturedMeasurements.some((m) => m.value_pass_fail === "FAIL")
                    ? "reject"
                    : "accept";

    async function finishAccept() {
        setBusy(true);
        try {
            if (!(await ensureFlushed())) { toast.error("Could not save inspection captures"); return; }
            // Persist the attribute count so the QR carries defectives_found and the
            // server-side acceptance evaluation matches.
            if (!isVariables && hasPlan) {
                try { await recordBulkMut.mutateAsync({ id: lotId, defectives_found: bd }); } catch { /* non-fatal */ }
            }
            await acceptMut.mutateAsync({ id: lotId });
            toast.success("Lot accepted");
            navigate({ to: "/production/receiving-inspection/$lotId", params: { lotId } });
        } catch {
            toast.error("Could not accept lot");
        } finally {
            setBusy(false);
        }
    }

    // Reject = open a nonconformance, not just a status flip. Mirrors the
    // receiving page: reject the lot, open a QuarantineDisposition linked to the
    // resulting report, optionally raise a SCAR.
    async function confirmReject(values: RejectDispositionValues) {
        setBusy(true);
        let dispositionOk = true;
        try {
            if (!(await ensureFlushed())) { toast.error("Could not save inspection captures"); return; }
            if (!isVariables && hasPlan) {
                try { await recordBulkMut.mutateAsync({ id: lotId, defectives_found: bd }); } catch { /* non-fatal */ }
            }
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
            if (values.raise_scar && lot?.supplier) {
                try { await scarMut.mutateAsync({ id: lotId }); } catch { /* non-fatal */ }
            }
            toast.success(dispositionOk ? "Lot rejected · disposition opened" : "Lot rejected (open the disposition manually)");
            navigate({ to: "/production/receiving-inspection/$lotId", params: { lotId } });
        } catch {
            toast.error("Could not reject lot");
        } finally {
            setBusy(false);
            setRejectOpen(false);
        }
    }

    const verdictBadge =
        verdict === "accept" ? <Badge className="bg-green-600 hover:bg-green-600">ACCEPT</Badge>
            : verdict === "reject" ? <Badge variant="destructive">REJECT</Badge>
                : <Badge variant="outline">In progress</Badge>;

    return (
        <div className="rounded-lg border bg-card p-5 space-y-4">
            <div className="flex items-center gap-3">
                <h2 className="text-lg font-semibold">Lot acceptance</h2>
                {verdictBadge}
                {samplePlan && (
                    <span className="text-xs text-muted-foreground">
                        {samplePlan.strategy}
                        {samplePlan.inspection_level ? ` · level ${samplePlan.inspection_level}` : ""}
                        {samplePlan.severity ? ` · ${samplePlan.severity}` : ""}
                    </span>
                )}
            </div>

            {/* Attribute (C=0 / Z1.4): the inspector records defectives in the sample. */}
            {!isVariables && hasPlan && (
                <div className="space-y-2">
                    {useByChar ? (
                        <>
                            <div className="text-sm font-medium">Defects found by characteristic (sample of {n})</div>
                            <div className="space-y-1.5">
                                {characteristics.map((c) => (
                                    <div key={c.id} className="flex items-center gap-2 text-sm">
                                        <span className="w-48 text-muted-foreground">{c.label}</span>
                                        <Input
                                            className="w-20" type="number" min={0}
                                            placeholder="0"
                                            value={defectByChar[String(c.id)] ?? ""}
                                            onChange={(e) => setDefectByChar((p) => ({ ...p, [String(c.id)]: e.target.value }))}
                                        />
                                        <span className="text-xs text-muted-foreground">defective</span>
                                    </div>
                                ))}
                            </div>
                        </>
                    ) : (
                        <div className="flex items-center gap-2 text-sm">
                            <span>Defectives found in the sample of <b>{n}</b></span>
                            <Input
                                className="w-24" type="number" min={0} value={defectTotal}
                                onChange={(e) => setDefectTotal(e.target.value)}
                            />
                        </div>
                    )}
                    <p className={`text-sm font-medium ${verdict === "reject" ? "text-destructive" : verdict === "accept" ? "text-green-600" : "text-muted-foreground"}`}>
                        Total defective: {bd} · Accept ≤ {ac} · Reject ≥ {re}
                        {verdict === "reject" && " — will REJECT"}
                        {verdict === "accept" && " — will ACCEPT"}
                    </p>
                </div>
            )}

            {/* Unit-by-unit: server-authoritative verdict over all recorded units. */}
            {unitMode && (
                <div className="space-y-2 text-sm">
                    {serverVerdict ? (
                        <div className="text-muted-foreground space-y-0.5">
                            {serverVerdict.is_variables ? (
                                <div>
                                    <b>{serverVerdict.readings}</b> of {serverVerdict.sample_size} readings recorded · k = <b>{serverVerdict.k}</b>
                                </div>
                            ) : (
                                <div>
                                    <b>{serverVerdict.defectives}</b> defective of {serverVerdict.units_recorded} units · Accept ≤ {serverVerdict.accept_number} · Reject ≥ {serverVerdict.reject_number}
                                </div>
                            )}
                            <div>Evaluated verdict: <b>{serverVerdict.status}</b></div>
                        </div>
                    ) : (
                        <p className="text-muted-foreground">
                            Record this unit's reading, then evaluate the lot over all {n} sampled units.
                        </p>
                    )}
                    {verdict === "pending" && (
                        <Button variant="outline" size="sm" disabled={evaluating || busy} onClick={evaluateOnServer}>
                            {evaluating ? "Evaluating…" : serverVerdict ? "Re-evaluate" : "Record reading & evaluate lot"}
                        </Button>
                    )}
                </div>
            )}

            {/* Variables (Z1.9), single-pass: verdict from the readings captured in-flow. */}
            {isVariables && !unitMode && (
                <div className="text-sm">
                    {variablesVerdict && variablesVerdict.state !== "pending" ? (
                        <div className="text-muted-foreground space-y-0.5">
                            <div>Measured <b>{varChar?.label}</b> · x̄ = {variablesVerdict.mean.toFixed(4)} · s = {variablesVerdict.s.toFixed(4)}</div>
                            {variablesVerdict.qu != null && <div>QU = (USL−x̄)/s = {variablesVerdict.qu.toFixed(3)}</div>}
                            {variablesVerdict.ql != null && <div>QL = (x̄−LSL)/s = {variablesVerdict.ql.toFixed(3)}</div>}
                            <div>k = {variablesVerdict.k.toFixed(3)} · accept if index ≥ k</div>
                        </div>
                    ) : (
                        <p className="text-muted-foreground">
                            Capture all {n} readings of {varChar?.label ?? "the characteristic"} to compute the verdict
                            ({variablesVerdict?.recorded ?? 0}/{n} recorded).
                        </p>
                    )}
                </div>
            )}

            {!hasPlan && !isVariables && (
                <p className="text-sm text-muted-foreground">
                    Disposition from the recorded inspection result.
                </p>
            )}

            <div className="flex gap-2 border-t pt-4">
                <Button
                    className="h-11 min-w-32"
                    disabled={busy || verdict === "pending"}
                    onClick={finishAccept}
                >
                    Accept lot
                </Button>
                <Button
                    variant="destructive" className="h-11 min-w-32"
                    disabled={busy}
                    onClick={() => setRejectOpen(true)}
                >
                    Reject lot
                </Button>
            </div>

            <RejectDispositionDialog
                open={rejectOpen}
                onOpenChange={setRejectOpen}
                lotNumber={lot?.lot_number ?? lotId}
                supplierName={lot?.supplier_name}
                hasSupplier={!!lot?.supplier}
                quantity={lot?.quantity ?? 0}
                defectives={isVariables ? undefined : bd}
                sampleSize={hasPlan ? n : undefined}
                acceptNumber={ac}
                defectBreakdown={defectBreakdown || undefined}
                submitting={busy}
                onConfirm={confirmReject}
            />
        </div>
    );
}
