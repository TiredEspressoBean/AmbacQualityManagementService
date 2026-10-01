import { LocationCombobox } from "@/components/locations/LocationCombobox";
/** Core lots — cores received in bulk, counted but not yet identified.
 *
 * Some cores arrive one by one with serials; some arrive forty to a pallet. The second
 * kind is received here as a LOT of the core type, and each unit is given its identity
 * — core number, part, core role — whenever the shop chooses: at receiving inspection,
 * when it is pulled for teardown, any time. From then on it is an ordinary exchange
 * core. Documents/CORE_AS_PART_DESIGN.md §6.
 *
 * Only exchange cores can arrive in bulk: a repair-and-return unit goes back to its
 * owner, so it needs its identity from the moment it is received. The server refuses a
 * lot for such a customer; this page says so before anyone tries.
 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { toast } from "sonner";
import { ArrowLeft, Boxes, Plus, Tag } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/generated";

import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import {
    useAssignCoreIdentity, useCoreLots, useReceiveCoreLot, type CoreLot,
} from "@/hooks/useCoreLots";

const GRADES = [
    { value: "A", label: "A — excellent" },
    { value: "B", label: "B — good" },
    { value: "C", label: "C — fair" },
    { value: "SCRAP", label: "Scrap — not usable" },
];

const SOURCES = [
    { value: "CUSTOMER_RETURN", label: "Customer return" },
    { value: "PURCHASED", label: "Purchased core" },
    { value: "WARRANTY", label: "Warranty return" },
    { value: "TRADE_IN", label: "Trade-in" },
];

const NO_CUSTOMER = "__none__";

function detailOf(err: unknown, fallback: string) {
    const data = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
    if (!data) return fallback;
    if (typeof data.detail === "string") return data.detail;
    const first = Object.values(data)[0];
    return Array.isArray(first) ? String(first[0]) : fallback;
}

function ReceiveLotDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
    const receive = useReceiveCoreLot();
    const { data: typesData } = useRetrievePartTypes({ limit: 500 });
    // Customers only: a lot is always received as a customer return (the service's
    // fixed source type), so a supplier-only company has no place here.
    const { data: companiesData } = useRetrieveCompanies({ limit: 200, is_customer: true });
    const [coreType, setCoreType] = useState("");

    // Offer only core types — the server's rule (services/reman/core_lot.is_core_type):
    // a type with a disassembly BOM, or one cores have already been received as. The
    // server still enforces it; this just stops the list offering what it would refuse.
    // Recent cores only (500): a type seen only in older cores and with no disassembly
    // BOM drops out of the list, which is the case its BOM should be authored for anyway.
    const bomQ = useQuery({
        queryKey: ["core-lots", "core-types", "disassembly-bom"],
        queryFn: () => api.api_DisassemblyBOMLines_list({ queries: { limit: 500 } }),
        enabled: open,
    });
    const coresQ = useQuery({
        queryKey: ["core-lots", "core-types", "cores"],
        queryFn: () => api.api_Cores_list({ queries: { limit: 500 } }),
        enabled: open,
    });
    const coreTypes = useMemo(() => {
        const ids = new Set<string>();
        for (const l of bomQ.data?.results ?? []) ids.add(String(l.core_type));
        for (const c of coresQ.data?.results ?? []) ids.add(String(c.core_type));
        return (typesData?.results ?? []).filter((t) => ids.has(String(t.id)));
    }, [typesData, bomQ.data, coresQ.data]);
    const typesLoading = bomQ.isLoading || coresQ.isLoading;
    const [quantity, setQuantity] = useState("");
    const [customer, setCustomer] = useState(NO_CUSTOMER);
    const [reference, setReference] = useState("");
    const [location, setLocation] = useState("");

    const customers = companiesData?.results ?? [];
    const chosen = customers.find((c) => String(c.id) === customer);
    // Said up front rather than left to a 400: their units go back to them, so each
    // must be received individually.
    const repairReturn = chosen?.default_core_fulfilment_mode === "REPAIR_RETURN";
    const qty = Number(quantity);
    const valid = !!coreType && Number.isInteger(qty) && qty > 0 && !repairReturn;

    const reset = () => {
        setCoreType(""); setQuantity(""); setCustomer(NO_CUSTOMER); setReference(""); setLocation("");
    };

    const submit = () =>
        receive.mutate(
            {
                core_type: coreType,
                quantity: qty,
                customer: customer === NO_CUSTOMER ? null : customer,
                source_reference: reference,
                storage_location: location,
            },
            {
                onSuccess: (lot) => {
                    toast.success(`Received ${lot.lot_number}: ${lot.quantity} × ${lot.core_type_name}`);
                    reset();
                    onOpenChange(false);
                },
                onError: (err) => toast.error(detailOf(err, "Could not receive the lot.")),
            },
        );

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Receive cores in bulk</DialogTitle>
                    <DialogDescription>
                        A counted delivery with no serials. Units are given identities later,
                        one at a time, and are exchange cores.
                    </DialogDescription>
                </DialogHeader>
                <div className="grid gap-3 text-sm">
                    <div className="grid gap-1">
                        <Label>Core type</Label>
                        <Select value={coreType || undefined} onValueChange={setCoreType}
                                disabled={typesLoading || coreTypes.length === 0}>
                            <SelectTrigger>
                                <SelectValue placeholder={typesLoading ? "Loading core types…" : "Choose the core type"} />
                            </SelectTrigger>
                            <SelectContent>
                                {coreTypes.map((t) => (
                                    <SelectItem key={String(t.id)} value={String(t.id)}>{t.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        {!typesLoading && coreTypes.length === 0 && (
                            <p className="text-xs text-muted-foreground">
                                No core types yet. Author a disassembly BOM for the unit, or receive
                                a first one individually, and it will appear here.
                            </p>
                        )}
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div className="grid gap-1">
                            <Label>Units counted</Label>
                            <Input inputMode="numeric" value={quantity}
                                   onChange={(e) => setQuantity(e.target.value.replace(/\D/g, ""))}
                                   placeholder="e.g. 40" />
                        </div>
                        <div className="grid gap-1">
                            <Label>Storage location</Label>
                            <LocationCombobox value={location} onChange={setLocation}
                                              placeholder="Optional — choose or type a location" />
                        </div>
                    </div>
                    <div className="grid gap-1">
                        <Label>From</Label>
                        <Select value={customer} onValueChange={setCustomer}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value={NO_CUSTOMER}>No customer recorded</SelectItem>
                                {customers.map((c) => (
                                    <SelectItem key={String(c.id)} value={String(c.id)}>{c.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        {repairReturn && (
                            <p className="text-xs text-destructive">
                                {chosen?.name}'s cores are repair-and-return — each goes back to
                                them, so receive them individually with their own identity.
                            </p>
                        )}
                    </div>
                    <div className="grid gap-1">
                        <Label>Reference</Label>
                        <Input value={reference} onChange={(e) => setReference(e.target.value)}
                               placeholder="RMA, packing slip, or the sender's own lot number" />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
                    <Button onClick={submit} disabled={!valid || receive.isPending}>
                        {receive.isPending ? "Receiving…" : "Receive lot"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function AssignIdentityDialog({ lot, onClose }: { lot: CoreLot | null; onClose: () => void }) {
    const assign = useAssignCoreIdentity();
    const [grade, setGrade] = useState("");
    const [serial, setSerial] = useState("");
    const [notes, setNotes] = useState("");
    const [source, setSource] = useState("CUSTOMER_RETURN");
    const [lastCore, setLastCore] = useState<{ id: string; number: string } | null>(null);
    // Bumped per unit so the grade Select remounts empty. Radix Select keeps showing
    // its last value when `value` goes back to undefined, so clearing state alone left
    // the previous unit's grade on screen with the buttons disabled.
    const [unit, setUnit] = useState(0);

    const clearUnit = () => { setGrade(""); setSerial(""); setNotes(""); setUnit((n) => n + 1); };

    // "Save and next": identifying units off a pallet is repetitive, so the dialog stays
    // open for the next one until the lot runs out.
    const submit = (next: boolean) => {
        if (!lot) return;
        assign.mutate(
            {
                lot: lot.id, condition_grade: grade as "A",
                serial_number: serial, condition_notes: notes, source_type: source as "CUSTOMER_RETURN",
            },
            {
                onSuccess: (core) => {
                    toast.success(`${core.core_number} identified from ${lot.lot_number}`);
                    setLastCore({ id: String(core.id), number: core.core_number ?? "" });
                    clearUnit();
                    if (!next || lot.unidentified <= 1) onClose();
                },
                onError: (err) => toast.error(detailOf(err, "Could not assign the identity.")),
            },
        );
    };

    return (
        <Dialog open={!!lot} onOpenChange={(o) => { if (!o) { clearUnit(); setLastCore(null); onClose(); } }}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Identify a unit from {lot?.lot_number}</DialogTitle>
                    <DialogDescription>
                        {lot?.core_type_name} · {lot?.unidentified} still unidentified. The unit
                        gets the next core number and becomes an exchange core.
                    </DialogDescription>
                </DialogHeader>
                <div className="grid gap-3 text-sm">
                    <div className="grid grid-cols-2 gap-3">
                        <div className="grid gap-1">
                            <Label>Condition</Label>
                            <Select key={unit} value={grade || undefined} onValueChange={setGrade}>
                                <SelectTrigger><SelectValue placeholder="Grade the unit" /></SelectTrigger>
                                <SelectContent>
                                    {GRADES.map((g) => <SelectItem key={g.value} value={g.value}>{g.label}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid gap-1">
                            <Label>Source</Label>
                            <Select value={source} onValueChange={setSource}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {SOURCES.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <div className="grid gap-1">
                        <Label>Serial number</Label>
                        <Input value={serial} onChange={(e) => setSerial(e.target.value)}
                               placeholder="If the unit carries one" />
                    </div>
                    <div className="grid gap-1">
                        <Label>Condition notes</Label>
                        <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
                    </div>
                    {lastCore && (
                        <p className="text-xs text-muted-foreground">
                            Last identified:{" "}
                            <Link to="/reman/cores/$id" params={{ id: lastCore.id }} className="underline">
                                {lastCore.number}
                            </Link>
                        </p>
                    )}
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => submit(false)} disabled={!grade || assign.isPending}>
                        Identify
                    </Button>
                    <Button onClick={() => submit(true)}
                            disabled={!grade || assign.isPending || (lot?.unidentified ?? 0) <= 1}>
                        Identify and next
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

export function CoreLotsPage() {
    const { data, isLoading } = useCoreLots();
    const [receiving, setReceiving] = useState(false);
    const [identifying, setIdentifying] = useState<CoreLot | null>(null);
    const lots = data ?? [];
    // Keep the dialog's count live as units are identified.
    const liveLot = useMemo(
        () => (identifying ? lots.find((l) => l.id === identifying.id) ?? identifying : null),
        [identifying, lots],
    );
    const unidentified = lots.reduce((n, l) => n + l.unidentified, 0);

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <Link to="/reman" className="mb-1 inline-flex items-center text-sm text-muted-foreground hover:underline">
                        <ArrowLeft className="mr-1 h-4 w-4" /> Remanufacturing
                    </Link>
                    <h1 className="flex items-center gap-2 text-2xl font-bold">
                        <Boxes className="h-6 w-6" /> Core lots
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        Cores received in bulk and not yet identified. They count in the core
                        bank now; each gets its identity when you pull it.
                    </p>
                </div>
                <Button onClick={() => setReceiving(true)}>
                    <Plus className="mr-2 h-4 w-4" /> Receive in bulk
                </Button>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>In the bank</CardTitle>
                    <CardDescription className="tabular-nums">
                        {isLoading ? "Loading…" : `${unidentified} unidentified unit${unidentified === 1 ? "" : "s"} across ${lots.length} lot${lots.length === 1 ? "" : "s"}`}
                    </CardDescription>
                </CardHeader>
                <CardContent className="overflow-x-auto">
                    {isLoading ? (
                        <Skeleton className="h-24 w-full" />
                    ) : lots.length === 0 ? (
                        <p className="py-6 text-center text-sm text-muted-foreground">
                            No bulk lots waiting. Cores that arrive counted but without serials
                            are received here with <span className="font-medium">Receive in bulk</span>.
                        </p>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Lot</TableHead>
                                    <TableHead>Core type</TableHead>
                                    <TableHead>From</TableHead>
                                    <TableHead>Received</TableHead>
                                    <TableHead className="text-right">Unidentified</TableHead>
                                    <TableHead>Location</TableHead>
                                    <TableHead />
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {lots.map((lot) => (
                                    <TableRow key={lot.id}>
                                        <TableCell className="font-mono text-xs">
                                            {lot.lot_number}
                                            {lot.source_reference && (
                                                <div className="text-muted-foreground">{lot.source_reference}</div>
                                            )}
                                        </TableCell>
                                        <TableCell>{lot.core_type_name}</TableCell>
                                        <TableCell>{lot.customer_name ?? "—"}</TableCell>
                                        <TableCell className="tabular-nums">{lot.received_date ?? "—"}</TableCell>
                                        <TableCell className="text-right tabular-nums">
                                            {lot.unidentified}
                                            <span className="text-muted-foreground"> / {lot.quantity}</span>
                                        </TableCell>
                                        <TableCell>{lot.storage_location || "—"}</TableCell>
                                        <TableCell className="text-right">
                                            <Button size="sm" variant="outline" onClick={() => setIdentifying(lot)}>
                                                <Tag className="mr-2 h-4 w-4" /> Identify a unit
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            <ReceiveLotDialog open={receiving} onOpenChange={setReceiving} />
            <AssignIdentityDialog lot={liveLot} onClose={() => setIdentifying(null)} />
        </div>
    );
}
