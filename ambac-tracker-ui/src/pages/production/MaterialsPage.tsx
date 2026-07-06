import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PackagePlus } from "lucide-react";
import type { Schema } from "@/lib/api/types";
import { useListMaterialLots } from "@/hooks/useListMaterialLots";

const col = createColumnHelper<Schema<"MaterialLot">>();

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    ACCEPTED: "default",
    AWAITING_INSPECTION: "secondary",
    REJECTED: "destructive",
    QUARANTINE: "destructive",
};

/**
 * Materials — the unified, status-segmented view of received purchased material.
 * Replaces the separate "Material Lots" + "Receiving Inspection" nav items: lots
 * are the same objects at different lifecycle stages, so we organize by STATUS
 * (the lens each role cares about) rather than by record type. Receiving clerks
 * use "+ Receive"; QA works the "Awaiting inspection" lens; planners read "On
 * hand"; supervisors read the funnel counts.
 */
type Tab = "awaiting" | "onhand" | "held" | "all";

const TABS: { id: Tab; label: string }[] = [
    { id: "awaiting", label: "Awaiting inspection" },
    { id: "onhand", label: "On hand" },
    { id: "held", label: "Held" },
    { id: "all", label: "All" },
];

/** Server-side filter for each lens. `inspection_pending` (RECEIVED +
 *  AWAITING_INSPECTION) is honored server-side; the rest map to a single status. */
function queriesForTab(tab: Tab): Record<string, unknown> {
    if (tab === "awaiting") return { inspection_pending: "true" };
    if (tab === "onhand") return { status: "ACCEPTED" };
    if (tab === "held") return { status: "QUARANTINE" };
    return {};
}

export function MaterialsPage() {
    const navigate = useNavigate();
    const [tab, setTab] = useState<Tab>("awaiting");

    // Funnel counts — cheap (limit:1, read total) and double as the manager's
    // at-a-glance of where material is piling up.
    const awaiting = useListMaterialLots({ inspection_pending: "true", limit: 1 } as never);
    const onhand = useListMaterialLots({ status: "ACCEPTED", limit: 1 } as never);
    const held = useListMaterialLots({ status: "QUARANTINE", limit: 1 } as never);
    const counts: Record<Tab, number | undefined> = {
        awaiting: awaiting.data?.count,
        onhand: onhand.data?.count,
        held: held.data?.count,
        all: undefined,
    };

    // List for the active lens. Defined inline so it closes over `tab`; the
    // ModelEditorPage is remounted per tab (key) to reset its pagination/search.
    const useList = (params: { offset: number; limit: number; ordering?: string; search?: string }) => {
        const q: Record<string, unknown> = { offset: params.offset, limit: params.limit, ...queriesForTab(tab) };
        if (params.ordering) q.ordering = params.ordering;
        if (params.search) q.search = params.search;
        // eslint-disable-next-line react-hooks/rules-of-hooks -- useList is itself a hook (use-prefixed), invoked unconditionally by ModelEditorPage
        return useListMaterialLots(q as never);
    };

    return (
        <ModelEditorPage
            key={tab}
            title="Materials"
            modelName="MaterialLots"
            useList={useList}
            headerContent={
                <div className="flex flex-wrap items-center gap-1.5 border-b pb-3">
                    {TABS.map((t) => (
                        <Button
                            key={t.id}
                            size="sm"
                            variant={tab === t.id ? "default" : "ghost"}
                            onClick={() => setTab(t.id)}
                        >
                            {t.label}
                            {counts[t.id] != null && (
                                <Badge variant="secondary" className="ml-2 tabular-nums">{counts[t.id]}</Badge>
                            )}
                        </Button>
                    ))}
                </div>
            }
            extraToolbarContent={
                <Button size="sm" onClick={() => navigate({ to: "/production/material-lots/receive" })}>
                    <PackagePlus className="h-4 w-4 mr-1" /> Receive
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
                    renderCell: (l) => (
                        <div className="flex items-center gap-1.5">
                            <Badge variant={STATUS_VARIANT[l.status] ?? "outline"}>{l.status}</Badge>
                            {l.hold_reason === "SUPPLIER_UNQUALIFIED" && (
                                <Badge variant="outline" className="border-amber-400 text-amber-700">Unqualified supplier</Badge>
                            )}
                        </div>
                    ),
                }),
                col({ header: "Received", renderCell: (l) => l.received_date ?? "—" }),
            ]}
            renderActions={(l) =>
                l.status === "AWAITING_INSPECTION" || l.status === "RECEIVED" ? (
                    <Button
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
