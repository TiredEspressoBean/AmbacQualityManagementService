import { useState } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileDown, FileUp, MoreHorizontal, PackagePlus, Truck } from "lucide-react";
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useReportEmail } from "@/hooks/useReportEmail";
import { AdjustLotQuantityDialog } from "@/components/receiving/AdjustLotQuantityDialog";
import { MoveLotDialog } from "@/components/locations/MoveLotDialog";
import { ChaseDeliveryDialog } from "@/components/receiving/ChaseDeliveryDialog";
import { RejectRemainderDialog, ShipBackDialog } from "@/components/receiving/LotReturnDialogs";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import type { Schema } from "@/lib/api/types";
import { useListMaterialLots } from "@/hooks/useListMaterialLots";
import { ExtendShelfLifeDialog } from "@/components/receiving/ExtendShelfLifeDialog";
import { ExpectedReceiptDialog } from "@/components/receiving/ExpectedReceiptDialog";
import { ImportExpectedReceiptsDialog } from "@/components/receiving/ImportExpectedReceiptsDialog";
import { ReceiptsExportDialog } from "@/components/receiving/ReceiptsExportDialog";
import { CancelExpectedReceiptDialog } from "@/components/receiving/CancelExpectedReceiptDialog";
import { ReceiveExpectedLotDialog } from "@/components/receiving/ReceiveExpectedLotDialog";
import { LotHoldBadges, canExtend } from "@/components/receiving/lotStatus";

type Lot = Schema<"MaterialLot">;
const col = createColumnHelper<Schema<"MaterialLot">>();

// Read as words, not codes — AWAITING_INSPECTION truncated on a tablet.
const STATUS_LABEL: Record<string, string> = {
    ON_ORDER: "On order", RECEIVED: "Received", AWAITING_INSPECTION: "Awaiting inspection",
    ACCEPTED: "Accepted", REJECTED: "Rejected", IN_USE: "In use", CONSUMED: "Consumed",
    SCRAPPED: "Scrapped", QUARANTINE: "Held", RETURNED: "Returned", CANCELLED: "Cancelled",
};

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
type Tab = "onorder" | "late" | "awaiting" | "onhand" | "held" | "rejected" | "all";

// Ordered by lifecycle stage: ordered → arrived, awaiting disposition → usable → held.
const TABS: { id: Tab; label: string }[] = [
    { id: "onorder", label: "On order" },
    // Overdue or due within a few days — what a buyer chases today.
    { id: "late", label: "Late" },
    { id: "awaiting", label: "Awaiting inspection" },
    { id: "onhand", label: "On hand" },
    { id: "held", label: "Held" },
    // Rejected, waiting on a disposition — and for return-to-supplier, the dock.
    { id: "rejected", label: "Rejected" },
    { id: "all", label: "All" },
];

/** Server-side filter for each lens. `inspection_pending` (RECEIVED +
 *  AWAITING_INSPECTION) is honored server-side; the rest map to a single status. */
function queriesForTab(tab: Tab): Record<string, unknown> {
    if (tab === "onorder") return { status: "ON_ORDER" };
    if (tab === "late") return { delivery: "late" };
    if (tab === "awaiting") return { inspection_pending: "true" };
    if (tab === "onhand") return { status: "ACCEPTED" };
    if (tab === "held") return { status: "QUARANTINE" };
    if (tab === "rejected") return { status: "REJECTED" };
    return {};
}

export function MaterialsPage() {
    const navigate = useNavigate();
    const { tab: asked } = useSearch({ strict: false }) as { tab?: string };
    const [tab, setTab] = useState<Tab>(
        TABS.some((t) => t.id === asked) ? (asked as Tab) : "awaiting");

    // Funnel counts — cheap (limit:1, read total) and double as the manager's
    // at-a-glance of where material is piling up.
    const onorder = useListMaterialLots({ status: "ON_ORDER", limit: 1 });
    const late = useListMaterialLots({ delivery: "late", limit: 1 });
    const awaiting = useListMaterialLots({ inspection_pending: "true", limit: 1 });
    const onhand = useListMaterialLots({ status: "ACCEPTED", limit: 1 });
    const held = useListMaterialLots({ status: "QUARANTINE", limit: 1 });
    const rejected = useListMaterialLots({ status: "REJECTED", limit: 1 });
    const counts: Record<Tab, number | undefined> = {
        onorder: onorder.data?.count,
        late: late.data?.count,
        awaiting: awaiting.data?.count,
        onhand: onhand.data?.count,
        held: held.data?.count,
        rejected: rejected.data?.count,
        all: undefined,
    };

    const [extendLot, setExtendLot] = useState<Lot | null>(null);
    const [expectOpen, setExpectOpen] = useState(false);
    const [importOpen, setImportOpen] = useState(false);
    const [receiptsOpen, setReceiptsOpen] = useState(false);
    const [adjustLot, setAdjustLot] = useState<Lot | null>(null);
    const [moveLot, setMoveLot] = useState<Lot | null>(null);
    const [chaseLot, setChaseLot] = useState<Lot | null>(null);
    const [cancelLot, setCancelLot] = useState<Lot | null>(null);
    const [shipLot, setShipLot] = useState<Lot | null>(null);
    const [remainderLot, setRemainderLot] = useState<Lot | null>(null);
    const canRejectWholeLot = usePermissionSet().has("reject_whole_lot");
    const { downloadReport } = useReportEmail();
    const onOrderLens = tab === "onorder" || tab === "late";
    const [receiveLot, setReceiveLot] = useState<Lot | null>(null);

    // List for the active lens. Defined inline so it closes over `tab`; the
    // ModelEditorPage is remounted per tab (key) to reset its pagination/search.
    const useList = (params: { offset: number; limit: number; ordering?: string; search?: string }) => {
        const q: Record<string, unknown> = { offset: params.offset, limit: params.limit, ...queriesForTab(tab) };
        if (params.ordering) q.ordering = params.ordering;
        if (params.search) q.search = params.search;
        return useListMaterialLots(q);
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
                                <Badge
                                    variant={t.id === "late" && (counts.late ?? 0) > 0 ? "destructive" : "secondary"}
                                    className="ml-2 tabular-nums"
                                >
                                    {counts[t.id]}
                                </Badge>
                            )}
                        </Button>
                    ))}
                </div>
            }
            extraToolbarContent={
                <div className="flex items-center gap-2">
                    <Button size="sm" variant="outline" onClick={() => setImportOpen(true)}>
                        <FileUp className="h-4 w-4 mr-1" /> Import POs
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setReceiptsOpen(true)}
                        title="What was received, by PO line, to post in the ERP">
                        <FileDown className="h-4 w-4 mr-1" /> Receipts for ERP
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setExpectOpen(true)}>
                        <Truck className="h-4 w-4 mr-1" /> Add expected delivery
                    </Button>
                    <Button size="sm" onClick={() => navigate({ to: "/production/material-lots/receive" })}>
                        <PackagePlus className="h-4 w-4 mr-1" /> Receive
                    </Button>
                </div>
            }
            sortOptions={
                // On order, nothing has been received yet — the useful axis is when it
                // lands, soonest first.
                onOrderLens
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
                col({
                    header: "Lot #",
                    renderCell: (l) => (
                        <button type="button" className="font-mono font-medium hover:underline"
                            onClick={() => navigate({ to: "/production/material-lots/$lotId", params: { lotId: String(l.id) } })}>
                            {l.lot_number}
                        </button>
                    ),
                }),
                // item_name resolves either side of the XOR (in-house PartType or purchased
                // Material) and falls back to the ad-hoc description. The older
                // material_type_name pairing rendered blank for every Material-based lot.
                col({
                    header: "Material",
                    renderCell: (l) => (
                        <span>
                            {l.item_name || "—"}
                            {l.owner_name && (
                                <Badge variant="outline" className="ml-1.5 border-sky-400 text-sky-700" title="Customer property — only their work may use it">
                                    {l.owner_name}&rsquo;s
                                </Badge>
                            )}
                        </span>
                    ),
                }),
                col({ header: "Supplier", renderCell: (l) => l.supplier_name ?? "—" }),
                ...(onOrderLens
                    ? [col({
                          header: "PO",
                          renderCell: (l) => l.erp_po_number
                              ? <span className="font-mono text-xs">{l.erp_po_number}{l.erp_po_line ? ` / ${l.erp_po_line}` : ""}</span>
                              : "—",
                      })]
                    : []),
                col({
                    header: "Qty",
                    // Once stock is drawn or adjusted, what's left is the number that matters.
                    renderCell: (l) => {
                        const unit = l.unit_of_measure ?? "";
                        const left = l.quantity_remaining;
                        return left != null && Number(left) !== Number(l.quantity)
                            ? <span>{`${left} ${unit}`.trim()} <span className="text-xs text-muted-foreground">of {l.quantity}</span></span>
                            : `${l.quantity ?? "—"} ${unit}`.trim();
                    },
                }),
                col({
                    header: "Status",
                    renderCell: (l) => (
                        <div className="flex items-center gap-1.5">
                            <Badge variant={STATUS_VARIANT[l.status ?? ""] ?? "outline"} className="whitespace-nowrap">
                                {STATUS_LABEL[l.status ?? ""] ?? l.status}
                            </Badge>
                            <LotHoldBadges lot={l} />
                        </div>
                    ),
                }),
                // An on-order lot has no receipt date — the date that matters is when it
                // is due to land, which is also what the planning lanes place it by.
                onOrderLens
                    ? col({
                          header: "Promised",
                          renderCell: (l) => (
                              <div>
                                  <div className="flex items-center gap-1.5">
                                      <span>{l.promised_date ?? "—"}</span>
                                      {l.delivery_state === "OVERDUE" && <Badge variant="destructive">Overdue</Badge>}
                                      {l.delivery_state === "DUE_SOON" && (
                                          <Badge className="bg-amber-500 text-white hover:bg-amber-500">Due soon</Badge>
                                      )}
                                  </div>
                                  {l.original_promised_date && l.original_promised_date !== l.promised_date && (
                                      <div className="text-xs text-muted-foreground">first promised {l.original_promised_date}</div>
                                  )}
                                  {l.chase_note && (
                                      <div className="max-w-56 truncate text-xs italic text-muted-foreground" title={l.chase_note}>
                                          Chased: {l.chase_note}
                                      </div>
                                  )}
                              </div>
                          ),
                      })
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
            // One primary action per row — what the lot is waiting for — and the rest in a
            // menu. Three buttons a row pushed Qty and Status off a tablet screen.
            renderActions={(l) => {
                const inStock = ["ACCEPTED", "IN_USE", "QUARANTINE", "AWAITING_INSPECTION", "RECEIVED"]
                    .includes(l.status ?? "");
                return (
                    <div className="flex items-center justify-end gap-1">
                        {l.status === "ON_ORDER" && (
                            <>
                                <Button size="sm" onClick={() => setReceiveLot(l)}>Receive</Button>
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <Button size="sm" variant="ghost" aria-label={`More actions for ${l.lot_number}`}>
                                            <MoreHorizontal className="h-4 w-4" />
                                        </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end">
                                        <DropdownMenuItem onSelect={() => setChaseLot(l)}>Chase…</DropdownMenuItem>
                                        <DropdownMenuItem onSelect={() => setCancelLot(l)}>
                                            Cancel expected receipt…
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            </>
                        )}
                        {!l.holds_cores && (l.status === "AWAITING_INSPECTION" || l.status === "RECEIVED" || l.status === "QUARANTINE") && (
                            <Button size="sm"
                                onClick={() => navigate({ to: "/production/receiving-inspection/$lotId", params: { lotId: String(l.id) } })}>
                                {l.status === "QUARANTINE" ? "Resolve" : "Inspect"}
                            </Button>
                        )}
                        {l.awaiting_return && (
                            <Button size="sm" onClick={() => setShipLot(l)}>Ship back</Button>
                        )}
                        {l.status !== "ON_ORDER" && (
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button size="sm" variant="ghost" aria-label={`More actions for ${l.lot_number}`}>
                                        <MoreHorizontal className="h-4 w-4" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                    <DropdownMenuItem onSelect={() => void downloadReport("material_lot_label",
                                        { lot_ids: [String(l.id)], copies: 1, layout: "thermal" })}>
                                        Print label
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onSelect={() => void downloadReport("material_lot_label",
                                        { lot_ids: [String(l.id)], copies: 1, layout: "sheet" })}>
                                        Print label (Letter sheet)
                                    </DropdownMenuItem>
                                    {inStock && (
                                        <DropdownMenuItem onSelect={() => setMoveLot(l)}>Move…</DropdownMenuItem>
                                    )}
                                    {inStock && (
                                        <DropdownMenuItem onSelect={() => setAdjustLot(l)}>Adjust quantity…</DropdownMenuItem>
                                    )}
                                    {/* The retained evidence of release (ISO 9001 §8.6). */}
                                    <DropdownMenuItem onSelect={() => void downloadReport("receiving_inspection_record",
                                        { lot_id: String(l.id) })}>
                                        Inspection record (PDF)
                                    </DropdownMenuItem>
                                    {canExtend(l) && (
                                        <DropdownMenuItem onSelect={() => setExtendLot(l)}>Extend shelf life…</DropdownMenuItem>
                                    )}
                                    {(l.awaiting_return || l.status === "RETURNED") && (
                                        <DropdownMenuItem onSelect={() => void downloadReport("rtv_sheet", { lot_id: String(l.id) })}>
                                            RTV sheet (PDF)
                                        </DropdownMenuItem>
                                    )}
                                    {canRejectWholeLot && (l.status === "ACCEPTED" || l.status === "IN_USE") && (
                                        <>
                                            <DropdownMenuSeparator />
                                            <DropdownMenuItem className="text-destructive focus:text-destructive"
                                                onSelect={() => setRemainderLot(l)}>Reject remaining stock…</DropdownMenuItem>
                                        </>
                                    )}
                                </DropdownMenuContent>
                            </DropdownMenu>
                        )}
                    </div>
                );
            }}
            showDetailsLink={false}
        />
        <ExpectedReceiptDialog open={expectOpen} onOpenChange={setExpectOpen} />
        <ImportExpectedReceiptsDialog open={importOpen} onOpenChange={setImportOpen} />
        <ReceiptsExportDialog open={receiptsOpen} onOpenChange={setReceiptsOpen} />
        {receiveLot && (
            <ReceiveExpectedLotDialog
                // Keyed by lot so the prefilled quantity resets between rows.
                key={String(receiveLot.id)}
                lotId={String(receiveLot.id)}
                itemName={receiveLot.item_name || receiveLot.lot_number}
                orderedQuantity={receiveLot.quantity}
                unitOfMeasure={receiveLot.unit_of_measure}
                purchaseUnit={receiveLot.item_purchase_unit}
                unitsPerPurchaseUnit={receiveLot.item_units_per_purchase_unit}
                requiresHeatNumber={receiveLot.item_requires_heat_number}
                onInspect={(id) =>
                    navigate({ to: "/production/receiving-inspection/$lotId", params: { lotId: id } })
                }
                open={receiveLot !== null}
                onOpenChange={(o) => { if (!o) setReceiveLot(null); }}
            />
        )}
        {chaseLot && (
            <ChaseDeliveryDialog key={String(chaseLot.id)} open
                target={{ lot_id: String(chaseLot.id), item_name: chaseLot.item_name ?? chaseLot.lot_number,
                          supplier_name: chaseLot.supplier_name, erp_po_number: chaseLot.erp_po_number,
                          erp_po_line: chaseLot.erp_po_line, promised_date: chaseLot.promised_date,
                          chase_note: chaseLot.chase_note }}
                onOpenChange={(o) => { if (!o) setChaseLot(null); }} />
        )}
        {cancelLot && (
            <CancelExpectedReceiptDialog
                key={String(cancelLot.id)}
                lotId={String(cancelLot.id)}
                label={cancelLot.erp_po_number
                    ? `PO ${cancelLot.erp_po_number}${cancelLot.erp_po_line ? ` / ${cancelLot.erp_po_line}` : ""} · ${cancelLot.item_name ?? ""}`
                    : `${cancelLot.lot_number} · ${cancelLot.item_name ?? ""}`}
                open={cancelLot !== null}
                onOpenChange={(o) => { if (!o) setCancelLot(null); }}
            />
        )}
        {moveLot && (
            <MoveLotDialog key={String(moveLot.id)}
                lot={{ id: String(moveLot.id), lot_number: moveLot.lot_number, storage_location: moveLot.storage_location,
                       quantity_remaining: moveLot.quantity_remaining, unit_of_measure: moveLot.unit_of_measure }}
                open={moveLot !== null} onOpenChange={(o) => { if (!o) setMoveLot(null); }} />
        )}
        {adjustLot && (
            <AdjustLotQuantityDialog
                key={String(adjustLot.id)}
                lotId={String(adjustLot.id)}
                lotNumber={adjustLot.lot_number}
                remaining={adjustLot.quantity_remaining}
                unitOfMeasure={adjustLot.unit_of_measure}
                open={adjustLot !== null}
                onOpenChange={(o) => { if (!o) setAdjustLot(null); }}
            />
        )}
        {shipLot && (
            <ShipBackDialog key={String(shipLot.id)} lotId={String(shipLot.id)} lotNumber={shipLot.lot_number}
                supplierName={shipLot.supplier_name} open={shipLot !== null}
                onOpenChange={(o) => { if (!o) setShipLot(null); }} />
        )}
        {remainderLot && (
            <RejectRemainderDialog key={String(remainderLot.id)} lotId={String(remainderLot.id)}
                lotNumber={remainderLot.lot_number} remaining={remainderLot.quantity_remaining}
                unitOfMeasure={remainderLot.unit_of_measure} open={remainderLot !== null}
                onOpenChange={(o) => { if (!o) setRemainderLot(null); }} />
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
