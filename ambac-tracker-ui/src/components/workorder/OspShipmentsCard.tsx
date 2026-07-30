/**
 * Read-oriented OSP shipments summary for the WO Detail page.
 *
 * Detail serves operators + non-lead QA. Send-out is a lead action and stays on
 * Control; here we surface visibility (what's at each vendor, what's back and
 * awaiting inspection) plus the entry point non-lead QA needs: open the return
 * inspection runtime for a RETURNED shipment.
 */
import { useState } from "react";
import { Loader2, Truck, PackageCheck } from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "@tanstack/react-router";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { useListOSPShipments } from "@/hooks/useOutsideProcess";
import { api } from "@/lib/api/generated";

function formatDate(value: string | null | undefined): string | null {
    if (!value) return null;
    const d = new Date(value);
    return isNaN(d.getTime()) ? null : d.toLocaleDateString();
}

async function openInspectionRuntime(
    shipmentId: string,
    navigate: ReturnType<typeof useNavigate>,
) {
    const plan = await api.api_OutsideProcessShipments_sample_plan_retrieve({
        params: { id: shipmentId },
    } as never) as { step_id?: string; step_execution_id?: string };
    if (plan.step_id && plan.step_execution_id) {
        navigate({
            to: "/operator/steps/$stepId/substeps",
            params: { stepId: String(plan.step_id) },
            search: {
                execution: String(plan.step_execution_id),
                osp_shipment: shipmentId,
                at: 0,
            } as never,
        });
    } else {
        toast.error("No open return inspection for this shipment.");
    }
}

export function OspShipmentsCard({ workOrderId }: { workOrderId: string }) {
    const { data, isLoading } = useListOSPShipments(workOrderId);
    const shipments = data?.results ?? [];

    // Nothing to show at all — skip the card so Detail stays quiet for WOs
    // that never leave the shop.
    if (!isLoading && shipments.length === 0) return null;

    const sent = shipments.filter((s) => s.status === "SENT");
    const returned = shipments.filter((s) => s.status === "RETURNED");
    const closed = shipments.filter((s) => s.status === "CLOSED");

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                    <Truck className="h-4 w-4" />
                    Outside processing
                    {sent.length > 0 && (
                        <Badge variant="outline" className="text-[10px]">
                            {sent.length} at vendor
                        </Badge>
                    )}
                    {returned.length > 0 && (
                        <Badge
                            variant="outline"
                            className="border-amber-400 text-amber-700 text-[10px]"
                        >
                            {returned.length} to inspect
                        </Badge>
                    )}
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
                {isLoading ? (
                    <p className="text-sm text-muted-foreground text-center py-2">
                        Loading shipments…
                    </p>
                ) : (
                    <>
                        {returned.map((s) => (
                            <ShipmentRow key={s.id} mode="inspect" shipment={s} />
                        ))}
                        {sent.map((s) => (
                            <ShipmentRow key={s.id} mode="sent" shipment={s} />
                        ))}
                        {closed.map((s) => (
                            <ShipmentRow key={s.id} mode="closed" shipment={s} />
                        ))}
                    </>
                )}
            </CardContent>
        </Card>
    );
}

type ShipmentLike = {
    id: string;
    shipment_number: string;
    supplier_name: string;
    step_name: string;
    quantity: number;
    shipped_at?: string | null;
    returned_at?: string | null;
};

function ShipmentRow({
    mode,
    shipment,
}: {
    mode: "sent" | "inspect" | "closed";
    shipment: ShipmentLike;
}) {
    const navigate = useNavigate();
    const [opening, setOpening] = useState(false);

    const handleInspect = async () => {
        setOpening(true);
        try {
            await openInspectionRuntime(shipment.id, navigate);
        } catch {
            toast.error("Couldn't open the return inspection.");
        } finally {
            setOpening(false);
        }
    };

    const shipped = formatDate(shipment.shipped_at);
    const returned = formatDate(shipment.returned_at);

    return (
        <div
            className={`flex items-center gap-3 rounded-md border px-3 py-2 text-sm ${
                mode === "inspect"
                    ? "bg-amber-500/10 border-amber-500/50"
                    : mode === "sent"
                    ? "bg-sky-500/10 border-sky-500/40"
                    : "bg-muted/30 border-muted"
            }`}
        >
            <PackageCheck className="h-4 w-4 text-muted-foreground shrink-0" />
            <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs">{shipment.shipment_number}</span>
                    <span className="text-xs text-muted-foreground truncate">
                        {shipment.step_name}
                    </span>
                </div>
                <div className="text-xs text-muted-foreground truncate">
                    {shipment.supplier_name} · {shipment.quantity} part
                    {shipment.quantity === 1 ? "" : "s"}
                    {mode === "sent" && shipped && <> · sent {shipped}</>}
                    {mode === "inspect" && returned && <> · returned {returned}</>}
                    {mode === "closed" && returned && <> · closed {returned}</>}
                </div>
            </div>
            {mode === "inspect" && (
                <Badge
                    variant="outline"
                    className="border-amber-400 text-amber-700 text-[10px] shrink-0"
                >
                    Returned
                </Badge>
            )}
            {mode === "sent" && (
                <Badge
                    variant="outline"
                    className="border-sky-400 text-sky-700 text-[10px] shrink-0"
                >
                    At vendor
                </Badge>
            )}
            {mode === "closed" && (
                <Badge variant="outline" className="text-[10px] shrink-0">
                    Closed
                </Badge>
            )}
            {mode === "inspect" && (
                <Button size="sm" onClick={handleInspect} disabled={opening}>
                    {opening && <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />}
                    Inspect
                </Button>
            )}
        </div>
    );
}
