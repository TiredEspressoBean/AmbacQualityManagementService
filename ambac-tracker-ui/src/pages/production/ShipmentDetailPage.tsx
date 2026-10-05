import { useState } from "react";
import { Link, useParams } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileCheck2, FileText, Pencil } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { RecordHistoryCard } from "@/components/data-management/RecordHistoryCard";
import { useReportEmail } from "@/hooks/useReportEmail";
import {
    errorOf, shipmentOptions, useUpdateShipment, useVoidShipment, type Shipment,
} from "@/hooks/useShipping";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="min-w-0">
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className="truncate text-sm">{children || "—"}</div>
        </div>
    );
}

/** One shipment: what left, to whom, under which paperwork — and its documents. */
export function ShipmentDetailPage() {
    const { shipmentId } = useParams({ strict: false }) as { shipmentId: string };
    const { data: s, isLoading } = useQuery(shipmentOptions(shipmentId));
    const { downloadReport } = useReportEmail();
    const [editOpen, setEditOpen] = useState(false);
    const [voidOpen, setVoidOpen] = useState(false);

    if (isLoading || !s) {
        return <div className="mx-auto max-w-5xl p-6"><div className="h-40 animate-pulse rounded bg-muted" /></div>;
    }

    return (
        <div className="mx-auto max-w-5xl space-y-4 p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <div className="text-sm text-muted-foreground">
                        <Link to="/production/shipments" className="hover:underline">Shipping</Link> / shipment
                    </div>
                    <h1 className="flex flex-wrap items-center gap-2 text-2xl font-semibold">
                        <span className="font-mono">{s.shipment_number}</span>
                        {s.is_voided ? <Badge variant="destructive">Voided</Badge> : <Badge variant="outline">Shipped</Badge>}
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        {s.parts.length} unit{s.parts.length === 1 ? "" : "s"}{s.lots.length > 0 ? ` and ${s.lots.length} lot${s.lots.length === 1 ? "" : "s"}` : ""} to {s.customer_name} on {new Date(s.shipped_at).toLocaleDateString()}
                        {s.shipped_by_name ? ` · ${s.shipped_by_name}` : ""}
                    </p>
                </div>
                <div className="flex flex-wrap gap-2">
                    {!s.is_voided && (
                        <>
                            <Button size="sm" variant="outline" onClick={() => void downloadReport("packing_list", { shipment_id: s.id })}>
                                <FileText className="mr-1 h-4 w-4" /> Packing list
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => void downloadReport("shipment_coc", { shipment_id: s.id })}>
                                <FileCheck2 className="mr-1 h-4 w-4" /> CoC
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => setEditOpen(true)}>
                                <Pencil className="mr-1 h-4 w-4" /> Edit paperwork
                            </Button>
                            <Button size="sm" variant="ghost" className="text-destructive" onClick={() => setVoidOpen(true)}>
                                Void…
                            </Button>
                        </>
                    )}
                </div>
            </div>

            {s.is_voided && (
                <p className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm">
                    Voided{s.voided_at ? ` on ${new Date(s.voided_at).toLocaleDateString()}` : ""}: {s.void_reason}. Its parts went back to where they waited.
                </p>
            )}

            <Card>
                <CardHeader className="pb-2"><CardTitle className="text-base">Paperwork</CardTitle></CardHeader>
                <CardContent className="grid grid-cols-2 gap-4 md:grid-cols-4">
                    <Field label="Carrier">{s.carrier}</Field>
                    <Field label="Tracking">{s.tracking_number}</Field>
                    <Field label="ERP shipper / packing slip">{s.reference}</Field>
                    <Field label="Expected delivery">{s.expected_delivery}</Field>
                    {s.requires_coc && <Field label="CoC">Required by this customer</Field>}
                    {s.notes && <div className="col-span-full text-sm"><span className="text-xs text-muted-foreground">Notes</span><div>{s.notes}</div></div>}
                </CardContent>
            </Card>

            {(s.parts.length > 0 || s.lots.length === 0) && (
            <Card>
                <CardHeader className="pb-2"><CardTitle className="text-base">{s.is_voided ? "Units it had" : "Units"}</CardTitle></CardHeader>
                <CardContent className="overflow-x-auto">
                    {s.parts.length === 0 ? (
                        <p className="text-sm text-muted-foreground">No units on this shipment{s.is_voided ? " — it was voided" : ""}.</p>
                    ) : (
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b text-left text-muted-foreground">
                                    <th className="py-2 pr-3 font-medium">Serial</th>
                                    <th className="py-2 pr-3 font-medium">Item</th>
                                    <th className="py-2 pr-3 font-medium">Work order</th>
                                    <th className="py-2 font-medium">Order</th>
                                </tr>
                            </thead>
                            <tbody>
                                {s.parts.map((p) => (
                                    <tr key={p.id} className="border-b last:border-0">
                                        <td className="py-2 pr-3 font-mono">{p.ERP_id}</td>
                                        <td className="py-2 pr-3">{p.part_type_name ?? "—"}</td>
                                        <td className="py-2 pr-3">{p.work_order_number ?? "—"}</td>
                                        <td className="py-2">{p.order_number ?? "—"}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </CardContent>
            </Card>
            )}

            {s.lots.length > 0 && (
                <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-base">{s.is_voided ? "Material it had" : "Material"}</CardTitle></CardHeader>
                    <CardContent className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b text-left text-muted-foreground">
                                    <th className="py-2 pr-3 font-medium">Lot</th>
                                    <th className="py-2 pr-3 font-medium">Item</th>
                                    <th className="py-2 text-right font-medium">Quantity</th>
                                </tr>
                            </thead>
                            <tbody>
                                {s.lots.map((l) => (
                                    <tr key={l.id} className="border-b last:border-0">
                                        <td className="py-2 pr-3"><Link to="/production/material-lots/$lotId" params={{ lotId: l.id }} className="font-mono hover:underline">{l.lot_number}</Link></td>
                                        <td className="py-2 pr-3">{l.item_name || "—"}</td>
                                        <td className="py-2 text-right tabular-nums">{l.quantity} {l.unit_of_measure}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </CardContent>
                </Card>
            )}

            <RecordHistoryCard endpoint="CustomerShipments" id={s.id} model="customershipment" />

            <EditPaperworkDialog shipment={s} open={editOpen} onOpenChange={setEditOpen} />
            <VoidShipmentDialog shipment={s} open={voidOpen} onOpenChange={setVoidOpen} />
        </div>
    );
}

function EditPaperworkDialog({ shipment, open, onOpenChange }: {
    shipment: Shipment; open: boolean; onOpenChange: (o: boolean) => void;
}) {
    const update = useUpdateShipment();
    const [carrier, setCarrier] = useState(shipment.carrier ?? "");
    const [tracking, setTracking] = useState(shipment.tracking_number ?? "");
    const [reference, setReference] = useState(shipment.reference ?? "");
    const [expected, setExpected] = useState(shipment.expected_delivery ?? "");
    const [notes, setNotes] = useState(shipment.notes ?? "");
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Paperwork · {shipment.shipment_number}</DialogTitle>
                    <DialogDescription>Tracking numbers and the ERP&rsquo;s shipper number often come after the truck leaves.</DialogDescription>
                </DialogHeader>
                <div className="grid gap-3 py-1 sm:grid-cols-2">
                    <div className="space-y-1.5"><Label htmlFor="ep-c">Carrier</Label><Input id="ep-c" value={carrier} onChange={(e) => setCarrier(e.target.value)} /></div>
                    <div className="space-y-1.5"><Label htmlFor="ep-t">Tracking number</Label><Input id="ep-t" value={tracking} onChange={(e) => setTracking(e.target.value)} /></div>
                    <div className="space-y-1.5"><Label htmlFor="ep-r">ERP shipper / packing slip no.</Label><Input id="ep-r" value={reference} onChange={(e) => setReference(e.target.value)} /></div>
                    <div className="space-y-1.5"><Label htmlFor="ep-e">Expected delivery</Label><Input id="ep-e" type="date" value={expected} onChange={(e) => setExpected(e.target.value)} /></div>
                    <div className="space-y-1.5 sm:col-span-2"><Label htmlFor="ep-n">Notes</Label><Textarea id="ep-n" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} /></div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={update.isPending}>Cancel</Button>
                    <Button disabled={update.isPending}
                        onClick={() => update.mutate({
                            id: shipment.id, carrier, tracking_number: tracking, reference,
                            expected_delivery: expected || null, notes,
                        }, {
                            onSuccess: () => { toast.success("Paperwork saved."); onOpenChange(false); },
                            onError: (e) => toast.error(errorOf(e, "Could not save")),
                        })}>
                        {update.isPending ? "Saving…" : "Save"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function VoidShipmentDialog({ shipment, open, onOpenChange }: {
    shipment: Shipment; open: boolean; onOpenChange: (o: boolean) => void;
}) {
    const voidIt = useVoidShipment();
    const [reason, setReason] = useState("");
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Void {shipment.shipment_number}?</DialogTitle>
                    <DialogDescription>
                        For a shipment recorded by mistake — the parts didn&rsquo;t go. They return to their
                        Ship step (sign-off runs again) or to stock. Goods that went and came back are a
                        return, not a void.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-1.5 py-1">
                    <Label htmlFor="vs-r">Reason</Label>
                    <Textarea id="vs-r" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={voidIt.isPending}>Cancel</Button>
                    <Button variant="destructive" disabled={voidIt.isPending || !reason.trim()}
                        onClick={() => voidIt.mutate({ id: shipment.id, reason }, {
                            onSuccess: () => { toast.success(`${shipment.shipment_number} voided.`); onOpenChange(false); },
                            onError: (e) => toast.error(errorOf(e, "Could not void")),
                        })}>
                        {voidIt.isPending ? "Voiding…" : "Void shipment"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
