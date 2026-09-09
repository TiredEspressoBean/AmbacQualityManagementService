import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PackagePlus, Truck } from "lucide-react";
import type { Schema } from "@/lib/api/types";
import { useListMaterialLots } from "@/hooks/useListMaterialLots";
import { ExtendShelfLifeDialog } from "@/components/receiving/ExtendShelfLifeDialog";
import { ExpectedReceiptDialog } from "@/components/receiving/ExpectedReceiptDialog";
import { ReceiveExpectedLotDialog } from "@/components/receiving/ReceiveExpectedLotDialog";
import { LotHoldBadges, canExtend } from "@/components/receiving/lotStatus";

type Lot = Schema<"MaterialLot">;
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
type Tab = "onorder" | "awaiting" | "onhand" | "held" | "all";

// Ordered by lifecycle stage: ordered → arrived, awaiting disposition → usable → held.
const TABS: { id: Tab; label: string }[] = [
    { id: "onorder", label: "On order" },
    { id: "awaiting", label: "Awaiting inspection" },
    { id: "onhand", label: "On hand" },
    { id: "held", label: "Held" },
    { id: "all", label: "All" },
];

/** Server-side filter for each lens. `inspection_pending` (RECEIVED +
 *  AWAITING_INSPECTION) is honored server-side; the rest map to a single status. */
function queriesForTab(tab: Tab): Record<string, unknown> {
    if (tab === "onorder") return { status: "ON_ORDER" };
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
    const onorder = useListMaterialLots({ status: "ON_ORDER", limit: 1 } as never);
    const awaiting = useListMaterialLots({ inspection_pending: "true", limit: 1 } as never);
    const onhand = useListMaterialLots({ status: "ACCEPTED", limit: 1 } as never);
    const held = useListMaterialLots({ status: "QUARANTINE", limit: 1 } as never);
    const counts: Record<Tab, number | undefined> = {
        onorder: onorder.data?.count,
        awaiting: awaiting.data?.count,
        onhand: onhand.data?.count,
        held: held.data?.count,
        all: undefined,
    };

    const [extendLot, setExtendLot] = useState<Lot | null>(null);
    const [expectOpen, setExpectOpen] = useState(false);
    const [receiveLot, setReceiveLot] = useState<Lot | null>(null);

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
        <>
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
                <div className="flex items-center gap-2">
                    <Button size="sm" variant="outline" onClick={() => setExpectOpen(true)}>
                        <Truck className="h-4 w-4 mr-1" /> Expect
                    </Button>
                    <Button size="sm" onClick={() => navigate({ to: "/production/material-lots/receive" })}>
                        <PackagePlus className="h-4 w-4 mr-1" /> Receive
                    </Button>
                </div>
            }
            sortOptions={
                // On order, nothing has been received yet — the useful axis is when it
                // lands, soonest first.
                tab === "onorder"
                    ? [
                          { label: "Promised (Soonest)", value: "promised_date" },
                          { label: "Promised (Latest)", value: "-promised_date" },
                          { label: "Lot # (A–Z)", value: "lot_number" },
                      ]
                    : [
                          { label: "Received (Newest)", value: "-received_date" },
                          { label: "Received (Oldest)", value: "received_date" },
                          { label: "Lot # (A–Z)", value: "lot_number" },
                      ]
            }
            columns={[
                col({ header: "Lot #", renderCell: (l) => <span className="font-mono font-medium">{l.lot_number}</span> }),
                // item_name resolves either side of the XOR (in-house PartType or purchased
                // Material) and falls back to the ad-hoc description. The older
                // material_type_name pairing rendered blank for every Material-based lot.
                col({ header: "Material", renderCell: (l) => l.item_name || "—" }),
                col({ header: "Supplier", renderCell: (l) => l.supplier_name ?? "—" }),
                col({ header: "Qty", renderCell: (l) => `${l.quantity ?? "—"} ${l.unit_of_measure ?? ""}`.trim() }),
                col({
                    header: "Status",
                    renderCell: (l) => (
                        <div className="flex items-center gap-1.5">
                            <Badge variant={STATUS_VARIANT[l.status ?? ""] ?? "outline"}>{l.status}</Badge>
                            <LotHoldBadges lot={l} />
                        </div>
                    ),
                }),
                // An on-order lot has no receipt date — the date that matters is when it
                // is due to land, which is also what the planning lanes place it by.
                tab === "onorder"
                    ? col({ header: "Promised", renderCell: (l) => l.promised_date ?? "—" })
                    : col({
                          header: "Received",
                          // Who took it in, under the date — the AS9100 question about a
                          // lot is "who accepted this material", and it costs no extra
                          // query since received_by is already select_related.
                          renderCell: (l) => (
                              <div className="leading-tight">
                                  <div>{l.received_date ?? "—"}</div>
                                  {l.received_by_name && (
                                      <div className="text-xs text-muted-foreground">
                                          {l.received_by_name}
                                      </div>
                                  )}
                              </div>
                          ),
                      }),
            ]}
            renderActions={(l) => (
                <div className="flex items-center gap-2">
                    {l.status === "ON_ORDER" && (
                        <Button size="sm" onClick={() => setReceiveLot(l)}>
                            Receive
                        </Button>
                    )}
                    {canExtend(l) && (
                        <Button size="sm" variant="outline" onClick={() => setExtendLot(l)}>
                            Extend shelf life
                        </Button>
                    )}
                    {(l.status === "AWAITING_INSPECTION" || l.status === "RECEIVED") && (
                        <Button
                            size="sm"
                            onClick={() => navigate({ to: "/production/receiving-inspection/$lotId", params: { lotId: String(l.id) } })}
                        >
                            Inspect
                        </Button>
                    )}
                </div>
            )}
            showDetailsLink={false}
        />
        <ExpectedReceiptDialog open={expectOpen} onOpenChange={setExpectOpen} />
        {receiveLot && (
            <ReceiveExpectedLotDialog
                // Keyed by lot so the prefilled quantity resets between rows.
                key={String(receiveLot.id)}
                lotId={String(receiveLot.id)}
                itemName={receiveLot.item_name || receiveLot.lot_number}
                orderedQuantity={receiveLot.quantity}
                unitOfMeasure={receiveLot.unit_of_measure}
                onInspect={(id) =>
                    navigate({ to: "/production/receiving-inspection/$lotId", params: { lotId: id } })
                }
                open={receiveLot !== null}
                onOpenChange={(o) => { if (!o) setReceiveLot(null); }}
            />
        )}
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
