import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Schema } from "@/lib/api/types";
import { useListMaterialLots } from "@/hooks/useListMaterialLots";
import { ExtendShelfLifeDialog } from "@/components/receiving/ExtendShelfLifeDialog";

type Lot = Schema<"MaterialLot">;
// A lot the operator can re-qualify: held for shelf life, or already flagged EXPIRED.
const canExtend = (l: Lot) => l.hold_reason === "SHELF_LIFE_EXPIRED" || l.shelf_life_status === "EXPIRED";

const col = createColumnHelper<Schema<"MaterialLot">>();

// System-set MaterialLot.hold_reason codes → operator-facing labels (mirrors the
// vocabulary in services/qms/receiving_inspection.py).
const HOLD_LABELS: Record<string, string> = {
    SUPPLIER_UNQUALIFIED: "Unqualified supplier",
    PART_UNAPPROVED: "Unapproved part",
    SHELF_LIFE_EXPIRED: "Shelf life expired",
};

// Queue = lots still needing a disposition: RECEIVED (inspection not yet started)
// + AWAITING_INSPECTION (in progress). `inspection_pending` is honored server-side.
function useQueueList(params: { offset: number; limit: number; ordering?: string; search?: string }) {
    const queries: Record<string, unknown> = { offset: params.offset, limit: params.limit, inspection_pending: "true" };
    if (params.ordering) queries.ordering = params.ordering;
    if (params.search) queries.search = params.search;
    return useListMaterialLots(queries as never);
}

export function ReceivingInspectionQueuePage() {
    const navigate = useNavigate();
    const [extendLot, setExtendLot] = useState<Lot | null>(null);
    return (
        <>
        <ModelEditorPage
            title="Receiving Inspection Queue"
            modelName="MaterialLots"
            useList={useQueueList}
            columns={[
                col({ header: "Lot #", renderCell: (l) => <span className="font-mono font-medium">{l.lot_number}</span> }),
                col({ header: "Material", renderCell: (l) => l.material_type_name ?? l.material_description ?? "—" }),
                col({ header: "Supplier", renderCell: (l) => l.supplier_name ?? "—" }),
                col({ header: "Qty", renderCell: (l) => `${l.quantity ?? "—"} ${l.unit_of_measure ?? ""}`.trim() }),
                col({
                    header: "Status",
                    renderCell: (l) => (
                        <div className="flex items-center gap-1.5">
                            <Badge variant={l.status === "QUARANTINE" ? "destructive" : "secondary"}>{l.status}</Badge>
                            {HOLD_LABELS[l.hold_reason ?? ""] && (
                                <Badge variant="outline" className="border-amber-400 text-amber-700">{HOLD_LABELS[l.hold_reason ?? ""]}</Badge>
                            )}
                            {l.shelf_life_status === "WARNING" && l.hold_reason !== "SHELF_LIFE_EXPIRED" && (
                                <Badge variant="outline" className="border-amber-400 text-amber-700">Nearing expiry</Badge>
                            )}
                        </div>
                    ),
                }),
            ]}
            renderActions={(l) => (
                <div className="flex items-center gap-2">
                    {canExtend(l) && (
                        <Button size="sm" variant="outline" onClick={() => setExtendLot(l)}>
                            Extend shelf life
                        </Button>
                    )}
                    <Button
                        size="sm"
                        onClick={() => navigate({ to: "/production/receiving-inspection/$lotId", params: { lotId: String(l.id) } })}
                    >
                        Inspect
                    </Button>
                </div>
            )}
            showDetailsLink={false}
        />
        {extendLot && (
            <ExtendShelfLifeDialog
                lotId={String(extendLot.id)}
                lotNumber={extendLot.lot_number}
                currentExpiration={extendLot.expiration_date}
                open={extendLot !== null}
                onOpenChange={(o) => { if (!o) setExtendLot(null); }}
            />
        )}
        </>
    );
}
