/**
 * Outside-processing (subcontract, Flow B) panel for the WO Control page.
 *
 * Surfaces, per outside-process step in this work order:
 *   - parts sitting at the step, ready to ship → "Send out" (batch → one shipment)
 *   - shipments currently at a vendor → "Receive back" (opens the return
 *     inspection in the DWI operator runtime)
 *
 * Mirrors PendingDecisionsPanel's shape (self-contained, keyed by workOrderId).
 * Send-out is a supervisor/lead action — it lives here, alongside the other
 * per-step batch actions, not in the per-part operator runtime.
 */
import { useMemo, useState } from "react";
import { Loader2, Truck, PackageCheck } from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "@tanstack/react-router";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import { useRetrieveParts } from "@/hooks/parts";
import { useRetrieveProcessWithSteps } from "@/hooks/useRetrieveProcessWithSteps";
import { useListOSPShipments, useReceiveBack } from "@/hooks/useOutsideProcess";
import { useReportActivity } from "@/hooks/useReportActivity";
import { SendPartsOutDialog } from "@/components/workorder/SendPartsOutDialog";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";

type Step = components["schemas"]["Step"];
type PartRow = components["schemas"]["Parts"];

// A part is "ready to ship" only while it's actively AT the OSP step having
// arrived from the upstream step — i.e. IN_PROGRESS. This mirrors the shipper
// board's server-side rule (`_READY_TO_SHIP_STATUSES = {"IN_PROGRESS"}`); the
// two surfaces MUST agree on what's dispatchable. A prior blocklist here let
// PENDING / REWORK / already-returned (READY_FOR_NEXT_STEP, AWAITING_QA) parts
// count as ready, so the WO panel offered parts for send-out the board wouldn't.
const READY_TO_SHIP_STATUS = "IN_PROGRESS";

export function OutsideProcessPanel({
    workOrderId,
    processId,
    onActivity,
}: {
    workOrderId: string;
    processId: string | null;
    onActivity?: (active: boolean) => void;
}) {
    const { data: proc } = useRetrieveProcessWithSteps(
        { params: { id: processId ?? "" } },
        { enabled: !!processId },
    );
    const { data: partsData } = useRetrieveParts(
        { work_order: workOrderId, limit: 500 },
        undefined,
        { enabled: !!workOrderId },
    );
    const { data: shipmentsData } = useListOSPShipments(workOrderId);

    const ospSteps = useMemo<Step[]>(
        () => (proc?.process_steps ?? [])
            .map((ps) => ps.step)
            .filter((s) => s.is_outside_process),
        [proc],
    );

    const readyByStep = useMemo(() => {
        const m = new Map<string, PartRow[]>();
        for (const p of (partsData?.results ?? []) as PartRow[]) {
            if (!p.step) continue;
            if (String(p.part_status) !== READY_TO_SHIP_STATUS) continue;
            const arr = m.get(String(p.step)) ?? [];
            arr.push(p);
            m.set(String(p.step), arr);
        }
        return m;
    }, [partsData]);

    const allShipments = shipmentsData?.results ?? [];
    const sentShipments = allShipments.filter((s) => s.status === "SENT");
    const returnedShipments = allShipments.filter((s) => s.status === "RETURNED");

    const [dialogStep, setDialogStep] = useState<Step | null>(null);

    // Show only when there's actual OSP work: parts ready to dispatch, or
    // shipments out / awaiting return inspection. Keying on `ospSteps.length`
    // (does the process merely CONTAIN an OSP step?) rendered a near-empty
    // "Outside processing" header on every OSP-capable WO — noise, and it made
    // the "Needs attention" group light up with nothing actionable in it.
    // Only parts staged at THIS process's OSP steps count — readyByStep is
    // keyed by every step (the render reads it per-OSP-step via .get), so
    // summing the whole map would fold in parts sitting at non-OSP steps.
    const readyTotal = ospSteps.reduce((n, step) => n + (readyByStep.get(step.id)?.length ?? 0), 0);
    const hasActivity = readyTotal > 0 || sentShipments.length > 0 || returnedShipments.length > 0;
    useReportActivity(hasActivity, onActivity);
    if (!hasActivity) return null;

    return (
        <div className="rounded-lg border bg-card">
            <div className="flex items-center gap-2 border-b px-4 py-3">
                <Truck className="h-4 w-4 text-sky-600" />
                <span className="text-sm font-medium">Outside processing</span>
                {sentShipments.length > 0 && (
                    <Badge variant="outline" className="text-[10px]">
                        {sentShipments.length} at vendor
                    </Badge>
                )}
                {returnedShipments.length > 0 && (
                    <Badge variant="outline" className="border-amber-400 text-amber-700 text-[10px]">
                        {returnedShipments.length} to inspect
                    </Badge>
                )}
            </div>

            <div className="divide-y">
                {ospSteps.map((step) => {
                    const ready = readyByStep.get(step.id) ?? [];
                    return (
                        <div key={step.id} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                            <div className="min-w-0 flex-1">
                                <span className="font-medium">{step.name}</span>
                                <span className="ml-2 text-xs text-muted-foreground">
                                    {step.outside_supplier_name ?? "no default vendor"}
                                </span>
                            </div>
                            <span className="text-xs text-muted-foreground tabular-nums">
                                {ready.length} ready
                            </span>
                            <Button
                                size="sm"
                                variant="outline"
                                disabled={ready.length === 0}
                                onClick={() => setDialogStep(step)}
                            >
                                Send out
                            </Button>
                        </div>
                    );
                })}

                {sentShipments.map((s) => (
                    <ShipmentRow key={s.id} mode="receive" shipmentId={s.id} label={s.shipment_number}
                        vendor={s.supplier_name} qty={s.quantity} stepId={s.step} />
                ))}
                {returnedShipments.map((s) => (
                    <ShipmentRow key={s.id} mode="inspect" shipmentId={s.id} label={s.shipment_number}
                        vendor={s.supplier_name} qty={s.quantity} stepId={s.step} />
                ))}
            </div>

            {dialogStep && (
                <SendPartsOutDialog
                    stepId={dialogStep.id}
                    stepName={dialogStep.name}
                    defaultSupplierId={dialogStep.outside_supplier}
                    parts={(readyByStep.get(dialogStep.id) ?? []).map((p) => ({
                        id: p.id, label: p.ERP_id ?? p.id, status: String(p.part_status ?? ""),
                    }))}
                    onClose={() => setDialogStep(null)}
                />
            )}
        </div>
    );
}

/** Open a shipment's return inspection in the DWI operator runtime. */
async function openInspectionRuntime(
    shipmentId: string, navigate: ReturnType<typeof useNavigate>,
) {
    const plan = await api.api_OutsideProcessShipments_sample_plan_retrieve({
        params: { id: shipmentId },
    } as never) as { step_id?: string; step_execution_id?: string };
    if (plan.step_id && plan.step_execution_id) {
        navigate({
            to: "/operator/steps/$stepId/substeps",
            params: { stepId: String(plan.step_id) },
            search: { execution: String(plan.step_execution_id), osp_shipment: shipmentId, at: 0 } as never,
        });
    } else {
        toast.error("No open return inspection for this shipment.");
    }
}

function ShipmentRow({
    mode, shipmentId, label, vendor, qty, stepId,
}: {
    mode: "receive" | "inspect";
    shipmentId: string; label: string; vendor: string; qty: number; stepId: string;
}) {
    const navigate = useNavigate();
    const receiveBack = useReceiveBack();
    const [opening, setOpening] = useState(false);

    const handleReceive = () => {
        receiveBack.mutate({ id: shipmentId }, {
            onSuccess: async () => {
                toast.success(`${label} received — return inspection opened`);
                try { await openInspectionRuntime(shipmentId, navigate); } catch { /* reachable from the queue */ }
            },
        });
    };

    const handleInspect = async () => {
        setOpening(true);
        try { await openInspectionRuntime(shipmentId, navigate); }
        catch { toast.error("Couldn't open the return inspection."); }
        finally { setOpening(false); }
    };

    const busy = mode === "receive" ? receiveBack.isPending : opening;

    return (
        <div className="flex items-center gap-3 px-4 py-2.5 text-sm">
            <PackageCheck className="h-4 w-4 text-muted-foreground" />
            <div className="min-w-0 flex-1">
                <span className="font-mono text-xs">{label}</span>
                <span className="ml-2 text-xs text-muted-foreground">
                    {vendor} · {qty} part{qty === 1 ? "" : "s"}
                </span>
            </div>
            {mode === "inspect" && (
                <Badge variant="outline" className="border-amber-400 text-amber-700 text-[10px]">Returned</Badge>
            )}
            <Button
                size="sm"
                variant={mode === "inspect" ? "default" : "outline"}
                disabled={busy || !stepId}
                onClick={mode === "receive" ? handleReceive : handleInspect}
            >
                {busy && <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />}
                {mode === "receive" ? "Receive back" : "Inspect"}
            </Button>
        </div>
    );
}
