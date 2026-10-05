import { useMemo, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileCheck2, PackageCheck, Plus, Truck, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/generated";
import { resolveScan } from "@/lib/scan";
import { DataExportMenu } from "@/components/data-export-menu";
import { useReportEmail } from "@/hooks/useReportEmail";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import {
    deliveryPerformanceOptions, errorOf, readyToShipOptions, shipmentsOptions, useShipParts,
    type ReadyOrder,
} from "@/hooks/useShipping";

type Tab = "ready" | "shipped";
/** A material lot going on the shipment, and how much of it (blank = all). */
type LotPick = { id: string; lot_number: string; item_name: string; remaining: number; unit: string; quantity: string };

/**
 * The outbound dock. Parts waiting at their route's Ship step (or finished to stock)
 * are listed by order, and a customer's own material still here is listed under them;
 * pick what's going, record the carrier and the ERP's paperwork number, and it leaves
 * on one shipment. Our own material — surplus bar stock, a kit — ships from "Ship stock".
 * A customer who wants a CoC with every shipment gets it printed with the packing list.
 */
export function ShippingPage() {
    const [tab, setTab] = useState<Tab>("ready");
    const [search, setSearch] = useState("");
    const [stockOpen, setStockOpen] = useState(false);
    const ready = useQuery(readyToShipOptions());
    const shipped = useQuery({ ...shipmentsOptions(search), enabled: tab === "shipped" });
    const perf = useQuery(deliveryPerformanceOptions(90));
    const readyCount = (ready.data ?? []).reduce((n, g) => n + g.parts.length + g.lots.length, 0);

    return (
        <div className="mx-auto max-w-6xl space-y-4 p-6">
            <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-semibold tracking-tight">Shipping</h1>
                    <p className="text-sm text-muted-foreground">
                        What can go to customers now, and what has gone. Invoicing stays in your ERP.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button size="sm" variant="outline" onClick={() => setStockOpen(true)}>
                        <Truck className="mr-1 h-4 w-4" /> Ship stock…
                    </Button>
                    <div className="rounded-md border px-3 py-2 text-sm">
                        <span className="text-muted-foreground">On time, last 90 days: </span>
                        <span className="font-semibold tabular-nums">
                            {perf.data?.on_time_pct != null ? `${perf.data.on_time_pct}%` : "—"}
                        </span>
                        {perf.data && perf.data.deliveries > 0 && (
                            <span className="text-muted-foreground"> ({perf.data.on_time} of {perf.data.deliveries})</span>
                        )}
                    </div>
                </div>
            </div>

            <div className="flex gap-1 border-b">
                {([["ready", `Ready to ship${readyCount ? ` (${readyCount})` : ""}`], ["shipped", "Shipped"]] as const).map(([id, label]) => (
                    <Button key={id} size="sm" variant={tab === id ? "default" : "ghost"}
                        className="rounded-b-none" onClick={() => setTab(id)}>
                        {label}
                    </Button>
                ))}
            </div>

            {tab === "ready" ? (
                ready.isLoading ? <div className="h-32 animate-pulse rounded bg-muted" />
                    : (ready.data ?? []).length === 0 ? (
                        <p className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
                            <PackageCheck className="h-4 w-4" /> Nothing is waiting to ship. Parts appear here
                            when they reach their route&rsquo;s Ship step, or are finished to stock; a
                            customer&rsquo;s own material appears under them.
                        </p>
                    ) : (
                        <div className="space-y-3">
                            {ready.data!.map((g) => <ReadyOrderCard key={g.order_id ?? `owner-${g.customer_id}`} group={g} />)}
                        </div>
                    )
            ) : (
                <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                        <Input placeholder="Search shipment, customer, serial, tracking…" value={search}
                            onChange={(e) => setSearch(e.target.value)} className="max-w-sm" />
                        <DataExportMenu modelName="CustomerShipments" filename="shipments" size="sm" variant="outline"
                            className="ml-auto" {...(search ? { queryParams: { search } } : {})} />
                    </div>
                    <div className="overflow-x-auto rounded-lg border">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b text-left text-muted-foreground">
                                    <th className="px-3 py-2 font-medium">Shipment</th>
                                    <th className="px-3 py-2 font-medium">Customer</th>
                                    <th className="px-3 py-2 font-medium">Shipped</th>
                                    <th className="px-3 py-2 text-right font-medium">Units · lots</th>
                                    <th className="px-3 py-2 font-medium">Carrier · tracking</th>
                                    <th className="px-3 py-2 font-medium">Reference</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(shipped.data?.results ?? []).map((s) => (
                                    <tr key={s.id} className="border-b last:border-0">
                                        <td className="px-3 py-2">
                                            <Link to="/production/shipments/$shipmentId" params={{ shipmentId: s.id }}
                                                className="font-mono hover:underline">{s.shipment_number}</Link>
                                            {s.is_voided && <Badge variant="destructive" className="ml-2">Voided</Badge>}
                                        </td>
                                        <td className="px-3 py-2">{s.customer_name}</td>
                                        <td className="px-3 py-2 tabular-nums">{new Date(s.shipped_at).toLocaleDateString()}</td>
                                        <td className="px-3 py-2 text-right tabular-nums">
                                            {s.parts.length}{s.lots.length > 0 ? ` · ${s.lots.length} lot${s.lots.length === 1 ? "" : "s"}` : ""}
                                        </td>
                                        <td className="px-3 py-2">{[s.carrier, s.tracking_number].filter(Boolean).join(" · ") || "—"}</td>
                                        <td className="px-3 py-2 font-mono text-xs">{s.reference || "—"}</td>
                                    </tr>
                                ))}
                                {!shipped.isLoading && (shipped.data?.results ?? []).length === 0 && (
                                    <tr><td colSpan={6} className="px-3 py-8 text-center text-muted-foreground">No shipments yet.</td></tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {stockOpen && <ShipDialog group={null} partIds={[]} initialLots={[]} open onOpenChange={setStockOpen} onShipped={() => {}} />}
        </div>
    );
}

function ReadyOrderCard({ group }: { group: ReadyOrder }) {
    const [picked, setPicked] = useState<Set<string>>(new Set());
    const [pickedLots, setPickedLots] = useState<Set<string>>(new Set());
    const [open, setOpen] = useState(false);
    const toggle = (id: string) =>
        setPicked((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
    const toggleLot = (id: string) =>
        setPickedLots((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
    const count = picked.size + pickedLots.size;
    const lotPicks: LotPick[] = group.lots.filter((l) => pickedLots.has(l.id)).map((l) => ({
        id: l.id, lot_number: l.lot_number, item_name: l.item_name, remaining: l.quantity_remaining,
        unit: l.unit_of_measure, quantity: "",
    }));

    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="flex flex-wrap items-center gap-2 text-base">
                    {group.order_number
                        ? <Link to="/orders/$orderNumber" params={{ orderNumber: group.order_id! }} className="hover:underline">{group.order_number}</Link>
                        : <span className="text-muted-foreground">{group.lots.length > 0 && group.parts.length === 0 ? "Customer property" : "No order"}</span>}
                    <span className="font-normal text-muted-foreground">· {group.customer_name ?? "customer not set"}</span>
                    {group.requires_coc && (
                        <Badge variant="outline" className="gap-1"><FileCheck2 className="h-3 w-3" /> CoC with every shipment</Badge>
                    )}
                    <Button size="sm" className="ml-auto" disabled={count === 0} onClick={() => setOpen(true)}>
                        <Truck className="mr-1 h-4 w-4" /> Ship {count || ""}…
                    </Button>
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 overflow-x-auto">
                {group.parts.length > 0 && (
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b text-left text-muted-foreground">
                                <th className="w-8 py-2">
                                    <Checkbox checked={group.parts.every((p) => picked.has(p.id))} aria-label="Select all units"
                                        onCheckedChange={(v) => setPicked(v ? new Set(group.parts.map((p) => p.id)) : new Set())} />
                                </th>
                                <th className="py-2 pr-3 font-medium">Serial</th>
                                <th className="py-2 pr-3 font-medium">Item</th>
                                <th className="py-2 pr-3 font-medium">Work order</th>
                                <th className="py-2 pr-3 font-medium">Line · due</th>
                                <th className="py-2 font-medium">Waiting at</th>
                            </tr>
                        </thead>
                        <tbody>
                            {group.parts.map((p) => (
                                <tr key={p.id} className="border-b last:border-0">
                                    <td className="py-2"><Checkbox checked={picked.has(p.id)} onCheckedChange={() => toggle(p.id)} aria-label={`Ship ${p.erp_id}`} /></td>
                                    <td className="py-2 pr-3 font-mono">{p.erp_id}</td>
                                    <td className="py-2 pr-3">{p.part_type ?? "—"}</td>
                                    <td className="py-2 pr-3">{p.work_order ?? "—"}</td>
                                    <td className="py-2 pr-3 tabular-nums">
                                        {p.order_line != null ? `L${p.order_line}` : "—"}{p.due_date ? ` · ${p.due_date}` : ""}
                                    </td>
                                    <td className="py-2">{p.source === "STOCK" ? "Stock" : "Ship step"}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
                {group.lots.length > 0 && (
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b text-left text-muted-foreground">
                                <th className="w-8 py-2" />
                                <th className="py-2 pr-3 font-medium">Their material · lot</th>
                                <th className="py-2 pr-3 text-right font-medium">Here</th>
                                <th className="py-2 font-medium">Location</th>
                            </tr>
                        </thead>
                        <tbody>
                            {group.lots.map((l) => (
                                <tr key={l.id} className="border-b last:border-0">
                                    <td className="py-2"><Checkbox checked={pickedLots.has(l.id)} onCheckedChange={() => toggleLot(l.id)} aria-label={`Ship lot ${l.lot_number}`} /></td>
                                    <td className="py-2 pr-3">{l.item_name || "—"} <span className="font-mono text-xs text-muted-foreground">· {l.lot_number}</span></td>
                                    <td className="py-2 pr-3 text-right tabular-nums">{l.quantity_remaining} {l.unit_of_measure}</td>
                                    <td className="py-2">{l.storage_location || "—"}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </CardContent>
            {open && (
                <ShipDialog group={group} partIds={[...picked]} initialLots={lotPicks} open
                    onOpenChange={setOpen} onShipped={() => { setPicked(new Set()); setPickedLots(new Set()); }} />
            )}
        </Card>
    );
}

/** Add one of our own material lots to a shipment: scan its label or type the lot number. */
function AddLotField({ onAdd }: { onAdd: (l: LotPick) => void }) {
    const [code, setCode] = useState("");
    const add = async () => {
        const hit = await resolveScan(code).catch(() => null);
        if (hit?.kind !== "LOT") { toast.error(`No lot matches “${code.trim()}”.`); return; }
        const lot = await api.api_MaterialLots_retrieve({ params: { id: hit.id } });
        if (!["ACCEPTED", "IN_USE"].includes(lot.status ?? "")) {
            toast.error(`Lot ${lot.lot_number} is ${String(lot.status).toLowerCase()} — only accepted stock ships.`);
            return;
        }
        onAdd({ id: String(lot.id), lot_number: lot.lot_number, item_name: lot.item_name ?? "",
                remaining: Number(lot.quantity_remaining ?? 0), unit: lot.unit_of_measure ?? "", quantity: "" });
        setCode("");
    };
    return (
        <div className="flex gap-2">
            <Input placeholder="Scan or type a lot number" value={code} onChange={(e) => setCode(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); void add(); } }} />
            <Button type="button" variant="outline" onClick={() => void add()} disabled={!code.trim()}>
                <Plus className="mr-1 h-4 w-4" /> Add lot
            </Button>
        </div>
    );
}

function ShipDialog({ group, partIds, initialLots, open, onOpenChange, onShipped }: {
    group: ReadyOrder | null; partIds: string[]; initialLots: LotPick[]; open: boolean;
    onOpenChange: (o: boolean) => void; onShipped: () => void;
}) {
    const navigate = useNavigate();
    const ship = useShipParts();
    const { downloadReport } = useReportEmail();
    const customers = useRetrieveCompanies({ ordering: "name", limit: 1000, is_customer: true });
    const [customer, setCustomer] = useState<string>("");
    const [lots, setLots] = useState<LotPick[]>(initialLots);
    const [carrier, setCarrier] = useState("");
    const [tracking, setTracking] = useState("");
    const [reference, setReference] = useState("");
    const [expected, setExpected] = useState("");
    const [notes, setNotes] = useState("");
    const needsCustomer = !group?.customer_id;
    const customerList = useMemo(() => customers.data?.results ?? [], [customers.data]);
    const nothing = partIds.length === 0 && lots.length === 0;

    const submit = () => ship.mutate({
        part_ids: partIds,
        lots: lots.map((l) => ({ lot_id: l.id, quantity: l.quantity || null })),
        customer: needsCustomer ? customer || null : null,
        carrier, tracking_number: tracking, reference, notes,
        expected_delivery: expected || null,
    }, {
        onSuccess: (s) => {
            toast.success(`${s.shipment_number} shipped to ${s.customer_name}.`);
            void downloadReport("packing_list", { shipment_id: s.id });
            if (s.requires_coc) void downloadReport("shipment_coc", { shipment_id: s.id });
            onShipped();
            onOpenChange(false);
            void navigate({ to: "/production/shipments/$shipmentId", params: { shipmentId: s.id } });
        },
        onError: (e) => toast.error(errorOf(e, "Could not ship")),
    });

    const what = [
        partIds.length ? `${partIds.length} unit${partIds.length === 1 ? "" : "s"}` : "",
        lots.length ? `${lots.length} lot${lots.length === 1 ? "" : "s"}` : "",
    ].filter(Boolean).join(" and ");

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>{group ? `Ship ${what}` : "Ship stock"}</DialogTitle>
                    <DialogDescription>
                        {group?.customer_name ? `To ${group.customer_name}` : "Say who it's going to"}
                        {group?.order_number ? ` · ${group.order_number}` : ""}.
                        {partIds.length > 0 ? " Each part at a Ship step completes it, so its sign-off checks must be done." : ""}
                        {group?.requires_coc ? " The CoC prints with the packing list." : ""}
                    </DialogDescription>
                </DialogHeader>
                <div className="grid gap-3 py-1 sm:grid-cols-2">
                    {needsCustomer && (
                        <div className="space-y-1.5 sm:col-span-2">
                            <Label>Customer</Label>
                            <Select value={customer} onValueChange={setCustomer}>
                                <SelectTrigger><SelectValue placeholder="Choose the customer" /></SelectTrigger>
                                <SelectContent>
                                    {customerList.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                    )}
                    {(lots.length > 0 || !group) && (
                        <div className="space-y-1.5 sm:col-span-2">
                            <Label>Material</Label>
                            {lots.map((l) => (
                                <div key={l.id} className="flex items-center gap-2 text-sm">
                                    <span className="min-w-0 flex-1 truncate">{l.item_name || "—"} <span className="font-mono text-xs text-muted-foreground">· {l.lot_number}</span></span>
                                    <Input className="w-24" type="number" min={0} placeholder={`${l.remaining}`} value={l.quantity}
                                        aria-label={`Quantity of ${l.lot_number}`}
                                        onChange={(e) => setLots((xs) => xs.map((x) => x.id === l.id ? { ...x, quantity: e.target.value } : x))} />
                                    <span className="w-10 text-xs text-muted-foreground">{l.unit}</span>
                                    <Button type="button" size="sm" variant="ghost" aria-label={`Remove ${l.lot_number}`}
                                        onClick={() => setLots((xs) => xs.filter((x) => x.id !== l.id))}><X className="h-4 w-4" /></Button>
                                </div>
                            ))}
                            {!group && <AddLotField onAdd={(l) => setLots((xs) => xs.some((x) => x.id === l.id) ? xs : [...xs, l])} />}
                            <p className="text-xs text-muted-foreground">Blank quantity ships the whole lot; less splits that much off and the rest stays.</p>
                        </div>
                    )}
                    <div className="space-y-1.5">
                        <Label htmlFor="sh-carrier">Carrier</Label>
                        <Input id="sh-carrier" value={carrier} onChange={(e) => setCarrier(e.target.value)} placeholder="UPS Ground, customer pickup…" />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="sh-tracking">Tracking number <span className="text-muted-foreground">(can add later)</span></Label>
                        <Input id="sh-tracking" value={tracking} onChange={(e) => setTracking(e.target.value)} />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="sh-ref">ERP shipper / packing slip no. <span className="text-muted-foreground">(optional)</span></Label>
                        <Input id="sh-ref" value={reference} onChange={(e) => setReference(e.target.value)} />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="sh-exp">Expected delivery <span className="text-muted-foreground">(optional)</span></Label>
                        <Input id="sh-exp" type="date" value={expected} onChange={(e) => setExpected(e.target.value)} />
                    </div>
                    <div className="space-y-1.5 sm:col-span-2">
                        <Label htmlFor="sh-notes">Notes <span className="text-muted-foreground">(optional)</span></Label>
                        <Textarea id="sh-notes" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={ship.isPending}>Cancel</Button>
                    <Button onClick={submit} disabled={ship.isPending || nothing || (needsCustomer && !customer)}>
                        {ship.isPending ? "Shipping…" : "Ship"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
