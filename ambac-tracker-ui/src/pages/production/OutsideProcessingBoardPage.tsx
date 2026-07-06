/**
 * Outside Processing — shipper board (Supply).
 *
 * The dispatch surface for whoever ships parts to subcontract vendors — a
 * cross-work-order view, distinct from the per-WO send panel on the control page
 * and from the inspector's return queue (which lives in Incoming Inspection).
 *
 *   - "Ready to ship" — parts staged at OSP steps (finished upstream, not yet
 *     sent), grouped by step/vendor. The shipper batches a pallet and dispatches.
 *   - "At vendor" — shipments already out, awaiting return.
 *
 * Sending out is NOT an operator responsibility — it's a shipping/materials/lead
 * job, which is why it lives here (and on the control page) rather than the
 * operator runtime.
 */
import { useState } from "react";
import { Loader2, Truck, PackageCheck, Send } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useReadyToShip, useOSPShipments, type ReadyToShipGroup } from "@/hooks/useOutsideProcess";
import { SendPartsOutDialog } from "@/components/workorder/SendPartsOutDialog";

type Lens = "ready" | "at-vendor";

export function OutsideProcessingBoardPage() {
    const [lens, setLens] = useState<Lens>("ready");
    const { data: groups, isLoading: loadingReady } = useReadyToShip();
    const { data: shipmentsData, isLoading: loadingSent } = useOSPShipments({ status: "SENT" });
    const [dispatch, setDispatch] = useState<ReadyToShipGroup | null>(null);

    const readyGroups = groups ?? [];
    const sent = shipmentsData?.results ?? [];
    const readyTotal = readyGroups.reduce((n, g) => n + g.ready_count, 0);

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
                    At vendor{sent.length > 0 ? ` (${sent.length})` : ""}
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
                            <div key={s.id} className="flex items-center gap-3 px-4 py-3 text-sm">
                                <PackageCheck className="h-4 w-4 text-muted-foreground" />
                                <div className="min-w-0 flex-1">
                                    <span className="font-mono text-xs font-medium">{s.shipment_number}</span>
                                    <span className="ml-2 text-muted-foreground">
                                        {s.step_name} · {s.supplier_name} · {s.quantity} part{s.quantity === 1 ? "" : "s"}
                                    </span>
                                </div>
                                <Badge variant="outline" className="text-[10px]">Sent</Badge>
                            </div>
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
