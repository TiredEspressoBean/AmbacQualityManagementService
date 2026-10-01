import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { queryOptions, useQuery } from "@tanstack/react-query";
import { ArrowRight, FileText, Tag } from "lucide-react";
import { api } from "@/lib/api/generated";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RecordHistoryCard } from "@/components/data-management/RecordHistoryCard";
import { LotHoldBadges } from "@/components/receiving/lotStatus";
import { LotHoldPanel } from "@/components/receiving/LotHoldPanel";
import { materialLotOptions } from "@/hooks/useReceivingMutations";
import { useReportEmail } from "@/hooks/useReportEmail";
import type { Schema } from "@/lib/api/types";

type Trace = Schema<"LotTrace">;
type TracePart = Schema<"TracePart">;

const traceOptions = (lotId: string) =>
    queryOptions({
        queryKey: ["material-lot", lotId, "trace"],
        queryFn: () => api.api_MaterialLots_trace_retrieve({ params: { id: lotId } }) as Promise<Trace>,
    });

const STATUS_LABEL: Record<string, string> = {
    ON_ORDER: "On order", RECEIVED: "Received", AWAITING_INSPECTION: "Awaiting inspection",
    ACCEPTED: "Accepted", REJECTED: "Rejected", IN_USE: "In use", CONSUMED: "Consumed",
    SCRAPPED: "Scrapped", QUARANTINE: "Held", RETURNED: "Returned",
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="min-w-0">
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className="truncate text-sm">{children ?? "—"}</div>
        </div>
    );
}

function PartCell({ p }: { p: TracePart }) {
    return (
        <span>
            <span className="font-mono">{p.erp_id}</span>
            {p.part_type && <span className="text-muted-foreground"> · {p.part_type}</span>}
        </span>
    );
}

/**
 * One material lot: what it is, where it came from, where it went. The forward trace is
 * the recall question — every part this lot was drawn into, the assemblies those went
 * into, and the orders and customers they reached. It is only as complete as consumption
 * recording: a lot used without a step drawing from it leaves no trail.
 */
export function MaterialLotDetailPage() {
    const { lotId } = useParams({ strict: false }) as { lotId: string };
    const navigate = useNavigate();
    const { data: lot, isLoading } = useQuery(materialLotOptions(lotId));
    const { data: trace } = useQuery(traceOptions(lotId));
    const { downloadReport } = useReportEmail();

    if (isLoading || !lot) {
        return <div className="mx-auto max-w-5xl p-6"><div className="h-40 animate-pulse rounded bg-muted" /></div>;
    }
    const l = lot as Schema<"MaterialLot">;
    const unit = l.unit_of_measure ?? "";
    const b = trace?.backward;

    return (
        <div className="mx-auto max-w-5xl space-y-4 p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <div className="text-sm text-muted-foreground">
                        <Link to="/production/material-lots" className="hover:underline">Materials</Link> / lot
                    </div>
                    <h1 className="flex flex-wrap items-center gap-2 text-2xl font-semibold">
                        <span className="font-mono">{l.lot_number}</span>
                        <Badge variant="outline">{STATUS_LABEL[l.status ?? ""] ?? l.status}</Badge>
                        <LotHoldBadges lot={l} />
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        {l.item_name || "—"}
                        {l.owner_name && (
                            <span className="ml-2 font-medium text-sky-700">
                                Customer property — {l.owner_name}. Only their work may use it.
                            </span>
                        )}
                    </p>
                </div>
                <div className="flex flex-wrap gap-2">
                    {(l.status === "AWAITING_INSPECTION" || l.status === "RECEIVED" || l.status === "QUARANTINE") && (
                        <Button size="sm" onClick={() => navigate({ to: "/production/receiving-inspection/$lotId", params: { lotId } })}>
                            {l.status === "QUARANTINE" ? "Resolve" : "Inspect"}
                        </Button>
                    )}
                    {l.status !== "ON_ORDER" && (
                        <Button size="sm" variant="outline"
                            onClick={() => void downloadReport("material_lot_label", { lot_ids: [lotId], copies: 1, layout: "thermal" })}>
                            <Tag className="mr-1 h-4 w-4" /> Label
                        </Button>
                    )}
                    <Button size="sm" variant="outline"
                        onClick={() => void downloadReport("receiving_inspection_record", { lot_id: lotId })}>
                        <FileText className="mr-1 h-4 w-4" /> Inspection record
                    </Button>
                    {(l.awaiting_return || l.status === "RETURNED") && (
                        <Button size="sm" variant="outline"
                            onClick={() => void downloadReport("rtv_sheet", { lot_id: lotId })}>
                            RTV sheet
                        </Button>
                    )}
                </div>
            </div>

            <LotHoldPanel lot={l} />

            <Card>
                <CardHeader className="pb-2"><CardTitle className="text-base">The lot</CardTitle></CardHeader>
                <CardContent className="grid grid-cols-2 gap-4 md:grid-cols-4">
                    <Field label="On hand">{`${l.quantity_remaining ?? "—"} ${unit}`} <span className="text-muted-foreground">of {l.quantity}</span></Field>
                    <Field label="Counted as">{l.received_as_quantity && l.received_as_unit ? `${l.received_as_quantity} ${l.received_as_unit.toLowerCase()}` : null}</Field>
                    <Field label="Received">{l.received_date ? `${l.received_date}${l.received_by_name ? ` · ${l.received_by_name}` : ""}` : null}</Field>
                    <Field label="Location">{l.storage_location || null}</Field>
                    <Field label="Use by">{l.expiration_date ?? null}</Field>
                    <Field label="CoC">{l.certificate_of_conformance
                        ? <a className="underline" href={l.certificate_of_conformance as string} target="_blank" rel="noreferrer">On file</a>
                        : null}</Field>
                </CardContent>
            </Card>

            <div className="grid gap-4 md:grid-cols-2">
                <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-base">Came from</CardTitle></CardHeader>
                    <CardContent className="grid grid-cols-2 gap-4">
                        <Field label="Supplier">{b?.supplier}</Field>
                        <Field label="Their lot">{b?.supplier_lot_number}</Field>
                        <Field label="Heat number">{b?.heat_number}</Field>
                        <Field label="Bought from">{b?.source_type}</Field>
                        <Field label="ERP PO / line">{b?.erp_po}</Field>
                        <Field label="Split from">{b?.parent_lot_id
                            ? <Link to="/production/material-lots/$lotId" params={{ lotId: b.parent_lot_id }} className="font-mono underline">{b.parent_lot_number}</Link>
                            : null}</Field>
                        {(b?.split_lots.length ?? 0) > 0 && (
                            <div className="col-span-2">
                                <div className="text-xs text-muted-foreground">Split into</div>
                                <div className="flex flex-wrap gap-2 pt-1">
                                    {b!.split_lots.map((c) => (
                                        <Link key={c.lot_id} to="/production/material-lots/$lotId" params={{ lotId: c.lot_id }}>
                                            <Badge variant="outline" className="font-mono">
                                                {c.lot_number} · {c.quantity} · {STATUS_LABEL[c.status] ?? c.status}
                                            </Badge>
                                        </Link>
                                    ))}
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-base">Reached</CardTitle></CardHeader>
                    <CardContent className="space-y-2 text-sm">
                        {(trace?.customers.length ?? 0) === 0 ? (
                            <p className="text-muted-foreground">No customer yet — nothing drawn from this lot has reached an order.</p>
                        ) : (
                            <div className="flex flex-wrap gap-2">
                                {trace!.customers.map((c) => <Badge key={c}>{c}</Badge>)}
                            </div>
                        )}
                        <p className="text-xs text-muted-foreground">
                            Only what a step recorded drawing from this lot appears here.
                        </p>
                    </CardContent>
                </Card>
            </div>

            <Card>
                <CardHeader className="pb-2"><CardTitle className="text-base">Where it went</CardTitle></CardHeader>
                <CardContent>
                    {(trace?.forward.length ?? 0) === 0 ? (
                        <p className="text-sm text-muted-foreground">Nothing has been drawn from this lot yet.</p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b text-left text-muted-foreground">
                                        <th className="py-2 pr-3 font-medium">Used</th>
                                        <th className="py-2 pr-3 font-medium">Part</th>
                                        <th className="py-2 pr-3 font-medium">Built into</th>
                                        <th className="py-2 pr-3 font-medium">Work order · order</th>
                                        <th className="py-2 font-medium">Customer</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {trace!.forward.map((u, i) => {
                                        const top = u.built_into.length ? u.built_into[u.built_into.length - 1] : u.part;
                                        return (
                                            <tr key={i} className="border-b align-top last:border-0">
                                                <td className="py-2 pr-3 tabular-nums">{u.quantity} {unit}<div className="text-xs text-muted-foreground">{u.step ?? ""}</div></td>
                                                <td className="py-2 pr-3">{u.part ? <PartCell p={u.part} /> : "—"}</td>
                                                <td className="py-2 pr-3">
                                                    {u.built_into.length === 0 ? <span className="text-muted-foreground">—</span>
                                                        : u.built_into.map((a, j) => (
                                                            <span key={a.part_id} className="inline-flex items-center gap-1">
                                                                {j > 0 && <ArrowRight className="h-3 w-3 text-muted-foreground" />}
                                                                <PartCell p={a} />
                                                            </span>
                                                        ))}
                                                </td>
                                                <td className="py-2 pr-3">{[top?.work_order, top?.order].filter(Boolean).join(" · ") || "—"}</td>
                                                <td className="py-2">{top?.customer ?? "—"}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>

            <RecordHistoryCard endpoint="MaterialLots" id={lotId} model="materiallot" />
        </div>
    );
}
