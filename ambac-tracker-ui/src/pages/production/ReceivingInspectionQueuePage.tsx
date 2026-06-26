import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Schema } from "@/lib/api/types";
import { useListMaterialLots } from "@/hooks/useListMaterialLots";

const col = createColumnHelper<Schema<"MaterialLot">>();

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
    return (
        <ModelEditorPage
            title="Receiving Inspection Queue"
            modelName="MaterialLots"
            useList={useQueueList}
            columns={[
                col({ header: "Lot #", renderCell: (l) => <span className="font-mono font-medium">{l.lot_number}</span> }),
                col({ header: "Material", renderCell: (l) => l.material_type_name ?? l.material_description ?? "—" }),
                col({ header: "Supplier", renderCell: (l) => l.supplier_name ?? "—" }),
                col({ header: "Qty", renderCell: (l) => `${l.quantity ?? "—"} ${l.unit_of_measure ?? ""}`.trim() }),
                col({ header: "Status", renderCell: (l) => <Badge variant="secondary">{l.status}</Badge> }),
            ]}
            renderActions={(l) => (
                <Button
                    size="sm"
                    onClick={() => navigate({ to: "/production/receiving-inspection/$lotId", params: { lotId: String(l.id) } })}
                >
                    Inspect
                </Button>
            )}
            showDetailsLink={false}
        />
    );
}
