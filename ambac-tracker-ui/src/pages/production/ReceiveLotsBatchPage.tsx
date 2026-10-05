import { LocationCombobox } from "@/components/locations/LocationCombobox";
import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { StockItemCombobox, stockItemFields, useStockItems } from "@/components/receiving/StockItemCombobox";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import { useBulkCreateLots, type LotBulkRow } from "@/hooks/useReceivingMutations";
import { useReportEmail } from "@/hooks/useReportEmail";
import { locationSummaryOptions } from "@/hooks/useLocations";
import { SOURCE_TYPE_OPTIONS, type SourceType } from "@/components/receiving/lotStatus";

const NONE = "__none__";
const today = () => new Date().toISOString().slice(0, 10);

type Row = {
    lot_number: string;
    item: string; // "m:<material id>" / "p:<part type id>", or NONE
    supplier: string; // id or NONE
    supplier_lot_number: string;
    quantity: string;
    unit_of_measure: string;
    received_date: string;
    storage_location: string;
    /** "STOCK", or the item's buying unit — then Qty is boxes / pounds, converted server-side. */
    count_in: "STOCK" | "BOX" | "LB";
    heat_number: string;
    source_type: SourceType | typeof NONE;
    /** A customer's own material (free issue): theirs, not ours. NONE for our stock. */
    owner: string;
};

const emptyRow = (): Row => ({
    lot_number: "", item: NONE, supplier: NONE, supplier_lot_number: "",
    quantity: "", unit_of_measure: "EA", received_date: today(), storage_location: "",
    count_in: "STOCK", heat_number: "", source_type: NONE, owner: NONE,
});

// Column order used when pasting a spreadsheet without headers.
const PASTE_COLUMNS: (keyof Row)[] = [
    "lot_number", "item", "supplier", "quantity", "unit_of_measure", "received_date", "supplier_lot_number", "storage_location",
    "heat_number",
];

function parsePaste(text: string): string[][] {
    return text.replace(/\r\n/g, "\n").split("\n").filter((l) => l.length > 0)
        .map((line) => (line.includes("\t") ? line.split("\t") : line.split(",")));
}

export function ReceiveLotsBatchPage() {
    const navigate = useNavigate();
    const [rows, setRows] = useState<Row[]>([emptyRow()]);
    const [serverErrors, setServerErrors] = useState<Record<number, unknown>>({});
    const mutation = useBulkCreateLots();
    const { downloadReport } = useReportEmail();
    const stockItems = useStockItems();
    const { data: companies } = useRetrieveCompanies({ limit: 500, is_supplier: true });
    const { data: customers } = useRetrieveCompanies({ limit: 500, is_customer: true, ordering: "name" });

    const companyByName = useMemo(
        () => new Map((companies?.results ?? []).filter((c) => c.name).map((c) => [c.name.toLowerCase(), String(c.id)])),
        [companies],
    );

    // A location cell holds the location's id (picked) or, pasted from a sheet, its name
    // or code until it's matched — an unmatched one is a row error, not silently dropped.
    const { data: locs } = useQuery(locationSummaryOptions());
    const locationIds = useMemo(() => new Set((locs ?? []).map((l) => l.id)), [locs]);
    const locationByName = useMemo(() => {
        const m = new Map<string, string>();
        for (const l of locs ?? []) {
            m.set(l.name.toLowerCase(), l.id);
            if (l.code) m.set(l.code.toLowerCase(), l.id);
        }
        return m;
    }, [locs]);

    function setCell(idx: number, key: keyof Row, value: string) {
        setRows((prev) => prev.map((r, i) => (i === idx ? { ...r, [key]: value } : r)));
    }

    function handlePaste(e: React.ClipboardEvent<HTMLElement>) {
        const text = e.clipboardData.getData("text/plain");
        if (!text.includes("\t") && !text.includes("\n")) return; // normal single-cell paste
        e.preventDefault();
        const cells = parsePaste(text);
        const newRows = cells.map((cellRow) => {
            const r = emptyRow();
            cellRow.forEach((val, ci) => {
                const key = PASTE_COLUMNS[ci];
                if (!key) return;
                const v = val.trim();
                if (key === "item") r.item = stockItems.byName.get(v.toLowerCase()) ?? NONE;
                else if (key === "supplier") r.supplier = companyByName.get(v.toLowerCase()) ?? NONE;
                else if (key === "storage_location") r.storage_location = locationByName.get(v.toLowerCase()) ?? v;
                else (r as Record<string, string>)[key] = v;
            });
            return r;
        });
        setRows(newRows.length ? newRows : [emptyRow()]);
    }

    const rowErrors = (r: Row) => {
        const e: Partial<Record<keyof Row, string>> = {};
        if (!r.quantity.trim() || Number.isNaN(parseFloat(r.quantity))) e.quantity = "Invalid";
        if (!r.received_date) e.received_date = "Required";
        if (r.storage_location && !locationIds.has(r.storage_location)) e.storage_location = "Not a location";
        return e;
    };
    const hasErrors = rows.some((r) => Object.keys(rowErrors(r)).length > 0);

    function toPayload(r: Row): LotBulkRow {
        const out: LotBulkRow = {
            // Blank: the lot is numbered on receipt (LOT-<year>-00001).
            lot_number: r.lot_number.trim(),
            received_date: r.received_date,
            quantity: r.quantity.trim(),
        };
        // A lot is stock of a material OR a part — the picker says which, and only that
        // field is sent. (Materials were being sent as `material_type`, a PartType FK.)
        if (r.item !== NONE) Object.assign(out, stockItemFields(r.item));
        if (r.supplier !== NONE) out.supplier = r.supplier;
        if (r.supplier_lot_number.trim()) out.supplier_lot_number = r.supplier_lot_number.trim();
        if (r.unit_of_measure.trim()) out.unit_of_measure = r.unit_of_measure.trim();
        if (r.storage_location) out.location = r.storage_location;
        if (r.heat_number.trim()) out.heat_number = r.heat_number.trim();
        if (r.source_type !== NONE) out.source_type = r.source_type;
        if (r.owner !== NONE) out.owner = r.owner;
        if (r.count_in !== "STOCK") {
            out.received_as_quantity = r.quantity.trim();
            out.received_as_unit = r.count_in;
        }
        return out;
    }

    function submit() {
        if (hasErrors) { toast.error("Fix invalid rows before submitting"); return; }
        setServerErrors({});
        mutation.mutate(
            { lots: rows.map(toPayload) },
            {
                onSuccess: (data: { count?: number; created_lot_ids?: string[] }) => {
                    const ids = data?.created_lot_ids ?? [];
                    toast.success(`Received ${data?.count ?? rows.length} lot(s)`, ids.length
                        ? { action: { label: "Print labels",
                            onClick: () => void downloadReport("material_lot_label", { lot_ids: ids, copies: 1, layout: "thermal" }) } }
                        : undefined);
                    navigate({ to: "/production/material-lots" });
                },
                onError: (err: unknown) => {
                    const map: Record<number, unknown> = {};
                    const apiErr = err as { response?: { data?: { errors?: { index: number; errors: unknown }[] } } } | undefined;
                    for (const entry of apiErr?.response?.data?.errors ?? []) {
                        if (typeof entry.index === "number") map[entry.index] = entry.errors;
                    }
                    setServerErrors(map);
                    toast.error("Bulk receive failed");
                },
            },
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>Receive Lots</CardTitle>
                <p className="text-sm text-muted-foreground">
                    Paste rows from a spreadsheet (Lot #, Material or part, Supplier, Qty, Unit, Received, Supplier Lot, Location, Heat #) or add manually.
                    For an item bought by the box or pound, set &ldquo;Count in&rdquo; and enter boxes or the scale reading.
                </p>
            </CardHeader>
            <CardContent>
                <div onPaste={handlePaste} tabIndex={0} className="overflow-x-auto">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead title="Ours. Leave blank and one is assigned; the supplier's goes in Supplier Lot.">Lot #</TableHead>
                                <TableHead>Material / part</TableHead>
                                <TableHead>Supplier</TableHead>
                                <TableHead>Qty</TableHead>
                                <TableHead>Count in</TableHead>
                                <TableHead>Unit</TableHead>
                                <TableHead>Received</TableHead>
                                <TableHead>Supplier Lot</TableHead>
                                <TableHead>Location</TableHead>
                                <TableHead>Heat #</TableHead>
                                <TableHead>Source</TableHead>
                                <TableHead title="A customer's own material sent in for their job">Customer&rsquo;s own</TableHead>
                                <TableHead></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.map((r, idx) => {
                                const e = rowErrors(r);
                                return (
                                    <TableRow key={idx} className={serverErrors[idx] ? "bg-destructive/10" : ""}>
                                        <TableCell>
                                            <Input value={r.lot_number} placeholder="Assigned" onChange={(ev) => setCell(idx, "lot_number", ev.target.value)}
                                                className={`min-w-32 font-mono ${e.lot_number ? "border-destructive" : ""}`} />
                                        </TableCell>
                                        <TableCell>
                                            <StockItemCombobox className="min-w-44" aria-label={`Material or part, row ${idx + 1}`}
                                                items={stockItems} value={r.item === NONE ? null : r.item}
                                                onChange={(v) => {
                                                    setCell(idx, "item", v ?? NONE);
                                                    // The usual source, when nothing's chosen yet.
                                                    const pref = v ? stockItems.supplierOf.get(v) : null;
                                                    if (pref && r.supplier === NONE) setCell(idx, "supplier", pref);
                                                }}
                                                clearLabel="—" placeholder="—" />
                                        </TableCell>
                                        <TableCell>
                                            <Select value={r.supplier} onValueChange={(v) => setCell(idx, "supplier", v)}>
                                                <SelectTrigger className="min-w-32"><SelectValue /></SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value={NONE}>—</SelectItem>
                                                    {companies?.results?.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
                                                </SelectContent>
                                            </Select>
                                        </TableCell>
                                        <TableCell>
                                            <Input value={r.quantity} onChange={(ev) => setCell(idx, "quantity", ev.target.value)}
                                                className={`w-20 ${e.quantity ? "border-destructive" : ""}`} />
                                        </TableCell>
                                        <TableCell>
                                            <Select value={r.count_in} onValueChange={(v) => setCell(idx, "count_in", v)}>
                                                <SelectTrigger className="w-24" aria-label={`Count in, row ${idx + 1}`}><SelectValue /></SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="STOCK">Units</SelectItem>
                                                    <SelectItem value="BOX">Boxes</SelectItem>
                                                    <SelectItem value="LB">Pounds</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </TableCell>
                                        <TableCell><Input value={r.unit_of_measure} onChange={(ev) => setCell(idx, "unit_of_measure", ev.target.value)} className="w-16" /></TableCell>
                                        <TableCell><Input type="date" value={r.received_date} onChange={(ev) => setCell(idx, "received_date", ev.target.value)} className={e.received_date ? "border-destructive" : ""} /></TableCell>
                                        <TableCell><Input className="min-w-32 font-mono" value={r.supplier_lot_number} onChange={(ev) => setCell(idx, "supplier_lot_number", ev.target.value)} /></TableCell>
                                        <TableCell className="min-w-44">
                                            <LocationCombobox aria-label={`Storage location, row ${idx + 1}`} value={r.storage_location}
                                                onChange={(v) => setCell(idx, "storage_location", v ?? "")} placeholder="Location"
                                                selectedLabel={r.storage_location} />
                                        </TableCell>
                                        <TableCell>
                                            <Input value={r.heat_number} onChange={(ev) => setCell(idx, "heat_number", ev.target.value)}
                                                className="w-24 font-mono" aria-label={`Heat number, row ${idx + 1}`} />
                                        </TableCell>
                                        <TableCell>
                                            <Select value={r.source_type} onValueChange={(v) => setCell(idx, "source_type", v)}>
                                                <SelectTrigger className="min-w-32" aria-label={`Source, row ${idx + 1}`}><SelectValue /></SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value={NONE}>—</SelectItem>
                                                    {SOURCE_TYPE_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                                                </SelectContent>
                                            </Select>
                                        </TableCell>
                                        <TableCell>
                                            <Select value={r.owner} onValueChange={(v) => setCell(idx, "owner", v)}>
                                                <SelectTrigger className="min-w-32" aria-label={`Customer's own, row ${idx + 1}`}><SelectValue /></SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value={NONE}>— ours</SelectItem>
                                                    {customers?.results?.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
                                                </SelectContent>
                                            </Select>
                                        </TableCell>
                                        <TableCell>
                                            <Button variant="ghost" size="sm" onClick={() => setRows((p) => p.filter((_, i) => i !== idx))} disabled={rows.length === 1}>✕</Button>
                                        </TableCell>
                                    </TableRow>
                                );
                            })}
                        </TableBody>
                    </Table>
                </div>
                <div className="mt-4 flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setRows((p) => [...p, emptyRow()])}>Add Row</Button>
                    <Button size="sm" onClick={submit} disabled={mutation.isPending || hasErrors}>
                        {mutation.isPending ? "Receiving..." : `Receive ${rows.length} Lot(s)`}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => navigate({ to: "/production/material-lots" })}>Cancel</Button>
                </div>
            </CardContent>
        </Card>
    );
}
