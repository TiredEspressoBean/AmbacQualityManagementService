import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
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
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { useReportEmail } from "@/hooks/useReportEmail";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import { errorOf, useShipParts, type ReadyOrder } from "@/hooks/useShipping";

/** A material lot going on the shipment, and how much of it (blank = all). */
export type LotPick = { id: string; lot_number: string; item_name: string; remaining: number; unit: string; quantity: string };

/** Add one of our own material lots to a shipment: scan its label or type the lot number. */
function AddLotField({ onAdd }: { onAdd: (l: LotPick) => void }) {
    const [code, setCode] = useState("");
    const add = async () => {
        // resolveScan is null only for "no such code"; anything else is a failed lookup,
        // which must not read as "no lot matches" (walk 2026-10-26).
        let hit: Awaited<ReturnType<typeof resolveScan>>;
        try {
            hit = await resolveScan(code);
        } catch (e) {
            toast.error(apiErrorMessage(e) ?? "Couldn't look the lot up — try again.");
            return;
        }
        if (hit?.kind !== "LOT") { toast.error(`No lot matches “${code.trim()}”.`); return; }
        let lot;
        try {
            lot = await api.api_MaterialLots_retrieve({ params: { id: hit.id } });
        } catch (e) {
            toast.error(apiErrorMessage(e) ?? "Couldn't load the lot — try again.");
            return;
        }
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

export function ShipDialog({ group, partIds, initialLots, open, onOpenChange, onShipped }: {
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
