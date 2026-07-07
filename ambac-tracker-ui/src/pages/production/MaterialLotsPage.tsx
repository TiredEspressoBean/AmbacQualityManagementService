import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Schema } from "@/lib/api/types";
import { useListMaterialLots } from "@/hooks/useListMaterialLots";

const col = createColumnHelper<Schema<"MaterialLot">>();

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    ACCEPTED: "default",
    AWAITING_INSPECTION: "secondary",
    REJECTED: "destructive",
    QUARANTINE: "destructive",
};

function useMaterialLotsList(params: { offset: number; limit: number; ordering?: string; search?: string }) {
    const queries: Record<string, unknown> = { offset: params.offset, limit: params.limit };
    if (params.ordering) queries.ordering = params.ordering;
    if (params.search) queries.search = params.search;
    return useListMaterialLots(queries as never);
}

export function MaterialLotsPage() {
    const navigate = useNavigate();
    return (
        <ModelEditorPage
            title="Material Lots"
            modelName="MaterialLots"
            useList={useMaterialLotsList}
            extraToolbarContent={
                <Button size="sm" onClick={() => navigate({ to: "/production/material-lots/receive" })}>
                    Receive Lots
                </Button>
            }
            sortOptions={[
                { label: "Received (Newest)", value: "-received_date" },
                { label: "Received (Oldest)", value: "received_date" },
                { label: "Lot # (A–Z)", value: "lot_number" },
            ]}
            columns={[
                col({ header: "Lot #", renderCell: (l) => <span className="font-mono font-medium">{l.lot_number}</span> }),
                col({ header: "Material", renderCell: (l) => l.material_type_name ?? l.material_description ?? "—" }),
                col({ header: "Supplier", renderCell: (l) => l.supplier_name ?? "—" }),
                col({ header: "Qty", renderCell: (l) => `${l.quantity ?? "—"} ${l.unit_of_measure ?? ""}`.trim() }),
                col({
                    header: "Status",
                    renderCell: (l) => <Badge variant={STATUS_VARIANT[l.status ?? ""] ?? "outline"}>{l.status}</Badge>,
                }),
                col({ header: "Received", renderCell: (l) => l.received_date ?? "—" }),
            ]}
            renderActions={(l) =>
                l.status === "AWAITING_INSPECTION" || l.status === "RECEIVED" ? (
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigate({ to: "/production/receiving-inspection/$lotId", params: { lotId: String(l.id) } })}
                    >
                        Inspect
                    </Button>
                ) : null
            }
            showDetailsLink={false}
        />
    );
}
