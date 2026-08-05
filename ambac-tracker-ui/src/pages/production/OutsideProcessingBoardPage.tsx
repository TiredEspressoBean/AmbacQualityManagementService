/**
 * Outside Processing — shipper board (Supply).
 *
 * The dispatch surface for whoever ships parts to subcontract vendors — a
 * cross-work-order view, distinct from the per-WO send panel on the control page
 * and from the inspector's return queue (which lives in Incoming Inspection).
 *
 *   - "Ready to ship" — parts staged at OSP steps (finished upstream, not yet
 *     sent), grouped by step/vendor. The shipper batches a pallet and dispatches.
 *   - "At vendor" — shipments already out, each with a "Receive back" action
 *     that stamps the return and opens the return inspection. This closes the
 *     loop from the same cross-WO surface you dispatched from, so a shipper
 *     doesn't have to go find the owning work order's control page to record
 *     that a shipment came back (the per-WO panel still offers it too).
 *
 * Sending out is NOT an operator responsibility — it's a shipping/materials/lead
 * job, which is why it lives here (and on the control page) rather than the
 * operator runtime.
 */
import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { Loader2, Truck, PackageCheck, Send } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useReadyToShip, useOSPShipments, useReceiveBack, type ReadyToShipGroup } from "@/hooks/useOutsideProcess";
import { SendPartsOutDialog } from "@/components/workorder/SendPartsOutDialog";
import { api } from "@/lib/api/generated";

type Lens = "ready" | "at-vendor";

export function OutsideProcessingBoardPage() {
    const [lens, setLens] = useState<Lens>("ready");
    const { data: groups, isLoading: loadingReady } = useReadyToShip();
    const { data: shipmentsData, isLoading: loadingSent } = useOSPShipments({ status: "SENT" });
    const [dispatch, setDispatch] = useState<ReadyToShipGroup | null>(null);

    const readyGroups = groups ?? [];
    const sent = shipmentsData?.results ?? [];
    // Both header counts are in the SAME unit — parts. "Ready to ship" sums the
    // per-group part counts; "At vendor" sums parts across shipments (NOT the
    // shipment count, which read as a different unit and made two distinct
    // pairs of parts at the same step+vendor look like one batch shown twice).
    const readyTotal = readyGroups.reduce((n, g) => n + g.ready_count, 0);
    const sentTotal = sent.reduce((n, s) => n + (Number(s.quantity) || 0), 0);

    return (
        <div className="space-y-4 p-6">
            <div className="flex items-center gap-3">
                <Truck className="h-5 w-5 text-sky-600" />
                <h1 className="text-2xl font-semibold">Outside Processing</h1>
            </div>
            <p className="text-sm text-muted-foreground">
                Dispatch parts to subcontract vendors and track what's out. Grouped by step/vendor
                across work orders — batch a pallet and send. (Return inspection is in Incoming Inspection.)
            </p>

            <div className="flex gap-1 rounded-md border p-1 w-fit">
                <Button size="sm" variant={lens === "ready" ? "secondary" : "ghost"}
                    onClick={() => setLens("ready")}>
                    Ready to ship{readyTotal > 0 ? ` (${readyTotal})` : ""}
                </Button>
                <Button size="sm" variant={lens === "at-vendor" ? "secondary" : "ghost"}
                    onClick={() => setLens("at-vendor")}>
                    At vendor{sentTotal > 0 ? ` (${sentTotal})` : ""}
                </Button>
            </div>

            <div className="rounded-lg border bg-card">
                {lens === "ready" ? (
                    loadingReady ? (
                        <Loading />
                    ) : readyGroups.length === 0 ? (
                        <Empty text="Nothing staged for outside processing. Parts show up here when they reach an outside-process step." />
                    ) : (
                        <div className="divide-y">
                            {readyGroups.map((g) => (
                                <div key={g.step_id} className="flex items-center gap-3 px-4 py-3 text-sm">
                                    <Send className="h-4 w-4 text-muted-foreground" />
                                    <div className="min-w-0 flex-1">
                                        <span className="font-medium">{g.step_name}</span>
                                        <span className="ml-2 text-xs text-muted-foreground">
                                            {g.supplier_name ?? "no default vendor"}
                                        </span>
                                    </div>
                                    <span className="text-xs text-muted-foreground tabular-nums">
                                        {g.ready_count} ready
                                    </span>
                                    <Button size="sm" onClick={() => setDispatch(g)}>Send out</Button>
                                </div>
                            ))}
                        </div>
                    )
                ) : loadingSent ? (
                    <Loading />
                ) : sent.length === 0 ? (
                    <Empty text="Nothing out at a vendor right now." />
                ) : (
                    <div className="divide-y">
                        {sent.map((s) => (
                            <SentRow key={s.id} shipment={s} />
                        ))}
                    </div>
                )}
            </div>

            {dispatch && (
                <SendPartsOutDialog
                    stepId={dispatch.step_id}
                    stepName={dispatch.step_name}
                    defaultSupplierId={dispatch.supplier_id}
                    parts={dispatch.parts.map((p) => ({
                        id: p.id, label: p.erp_id || p.id, status: p.status,
                    }))}
                    onClose={() => setDispatch(null)}
                />
            )}
        </div>
    );
}

/** A SENT shipment row with a "Receive back" action. Mirrors the WO Control
 *  panel's receive flow: stamp the return (RETURNED + returned_at/by, parts →
 *  AWAITING_QA) then jump straight into the return inspection. `useReceiveBack`
 *  invalidates the OSP queries, so the shipment drops off "At vendor" here. */
function SentRow({
    shipment: s,
}: {
    shipment: {
        id: string | number;
        shipment_number?: string | null;
        step_name?: string | null;
        supplier_name?: string | null;
        quantity?: number | null;
    };
}) {
    const navigate = useNavigate();
    const receiveBack = useReceiveBack();
    const qty = Number(s.quantity) || 0;

    const handleReceive = () => {
        receiveBack.mutate({ id: String(s.id) }, {
            onSuccess: async () => {
                toast.success(`${s.shipment_number ?? "Shipment"} received — return inspection opened`);
                // Best-effort deep link; if it can't resolve, the inspection is
                // still reachable from Incoming Inspection.
                try { await openReturnInspection(String(s.id), navigate); } catch { /* noop */ }
            },
            onError: () => toast.error("Couldn't receive the shipment back."),
        });
    };

    return (
        <div className="flex items-center gap-3 px-4 py-3 text-sm">
            <PackageCheck className="h-4 w-4 text-muted-foreground" />
            <div className="min-w-0 flex-1">
                <span className="font-mono text-xs font-medium">{s.shipment_number}</span>
                <span className="ml-2 text-muted-foreground">
                    {s.step_name} · {s.supplier_name} · {qty} part{qty === 1 ? "" : "s"}
                </span>
            </div>
            <Badge variant="outline" className="text-[10px]">Sent</Badge>
            <Button size="sm" variant="outline" disabled={receiveBack.isPending} onClick={handleReceive}>
                {receiveBack.isPending && <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />}
                Receive back
            </Button>
        </div>
    );
}

/** Resolve a shipment's open return-inspection execution and navigate into the
 *  DWI runtime scoped to it. Same target the WO Control panel and Incoming
 *  Inspection use. */
async function openReturnInspection(shipmentId: string, navigate: ReturnType<typeof useNavigate>) {
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

function Loading() {
    return (
        <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
    );
}

function Empty({ text }: { text: string }) {
    return <div className="p-6 text-sm text-muted-foreground">{text}</div>;
}
