import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import { useBulkCreateLots, type LotBulkRow } from "@/hooks/useReceivingMutations";

const NONE = "__none__";
const today = () => new Date().toISOString().slice(0, 10);

type Row = {
    lot_number: string;
    material_type: string; // id or NONE
    supplier: string; // id or NONE
    supplier_lot_number: string;
    quantity: string;
    unit_of_measure: string;
    received_date: string;
    storage_location: string;
};

const emptyRow = (): Row => ({
    lot_number: "", material_type: NONE, supplier: NONE, supplier_lot_number: "",
    quantity: "", unit_of_measure: "EA", received_date: today(), storage_location: "",
});

// Column order used when pasting a spreadsheet without headers.
const PASTE_COLUMNS: (keyof Row)[] = [
    "lot_number", "material_type", "supplier", "quantity", "unit_of_measure", "received_date", "supplier_lot_number", "storage_location",
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
    const { data: partTypes } = useRetrievePartTypes({ limit: 500 } as never);
    const { data: companies } = useRetrieveCompanies({ limit: 500 } as never);

    const partTypeByName = useMemo(
        () => new Map((partTypes?.results ?? []).filter((p) => p.name).map((p) => [p.name.toLowerCase(), String(p.id)])),
        [partTypes],
    );
    const companyByName = useMemo(
        () => new Map((companies?.results ?? []).filter((c) => c.name).map((c) => [c.name.toLowerCase(), String(c.id)])),
        [companies],
    );

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
                if (key === "material_type") r.material_type = partTypeByName.get(v.toLowerCase()) ?? NONE;
                else if (key === "supplier") r.supplier = companyByName.get(v.toLowerCase()) ?? NONE;
                else (r as Record<string, string>)[key] = v;
            });
            return r;
        });
        setRows(newRows.length ? newRows : [emptyRow()]);
    }

    const rowErrors = (r: Row) => {
        const e: Partial<Record<keyof Row, string>> = {};
        if (!r.lot_number.trim()) e.lot_number = "Required";
        if (!r.quantity.trim() || Number.isNaN(parseFloat(r.quantity))) e.quantity = "Invalid";
        if (!r.received_date) e.received_date = "Required";
        return e;
    };
    const hasErrors = rows.some((r) => Object.keys(rowErrors(r)).length > 0);

    function toPayload(r: Row): LotBulkRow {
        const out: LotBulkRow = {
            lot_number: r.lot_number.trim(),
            received_date: r.received_date,
            quantity: r.quantity.trim(),
        };
        if (r.material_type !== NONE) out.material_type = r.material_type;
        if (r.supplier !== NONE) out.supplier = r.supplier;
        if (r.supplier_lot_number.trim()) out.supplier_lot_number = r.supplier_lot_number.trim();
        if (r.unit_of_measure.trim()) out.unit_of_measure = r.unit_of_measure.trim();
        if (r.storage_location.trim()) out.storage_location = r.storage_location.trim();
        return out;
    }

    function submit() {
        if (hasErrors) { toast.error("Fix invalid rows before submitting"); return; }
        setServerErrors({});
        mutation.mutate(
            { lots: rows.map(toPayload) },
            {
                onSuccess: (data: { count?: number }) => {
                    toast.success(`Received ${data?.count ?? rows.length} lot(s)`);
                    navigate({ to: "/production/material-lots" });
                },
                onError: (err: { response?: { data?: { errors?: { index: number; errors: unknown }[] } } }) => {
                    const map: Record<number, unknown> = {};
                    for (const entry of err.response?.data?.errors ?? []) {
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
                    Paste rows from a spreadsheet (Lot #, Material, Supplier, Qty, Unit, Received, Supplier Lot, Location) or add manually.
                </p>
            </CardHeader>
            <CardContent>
                <div onPaste={handlePaste} tabIndex={0} className="overflow-x-auto">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Lot #</TableHead>
                                <TableHead>Material</TableHead>
                                <TableHead>Supplier</TableHead>
                                <TableHead>Qty</TableHead>
                                <TableHead>Unit</TableHead>
                                <TableHead>Received</TableHead>
                                <TableHead>Supplier Lot</TableHead>
                                <TableHead>Location</TableHead>
                                <TableHead></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.map((r, idx) => {
                                const e = rowErrors(r);
                                return (
                                    <TableRow key={idx} className={serverErrors[idx] ? "bg-destructive/10" : ""}>
                                        <TableCell>
                                            <Input value={r.lot_number} onChange={(ev) => setCell(idx, "lot_number", ev.target.value)}
                                                className={e.lot_number ? "border-destructive" : ""} />
                                        </TableCell>
                                        <TableCell>
                                            <Select value={r.material_type} onValueChange={(v) => setCell(idx, "material_type", v)}>
                                                <SelectTrigger className="min-w-32"><SelectValue /></SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value={NONE}>—</SelectItem>
                                                    {partTypes?.results?.map((p) => <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>)}
                                                </SelectContent>
                                            </Select>
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
                                        <TableCell><Input value={r.unit_of_measure} onChange={(ev) => setCell(idx, "unit_of_measure", ev.target.value)} className="w-16" /></TableCell>
                                        <TableCell><Input type="date" value={r.received_date} onChange={(ev) => setCell(idx, "received_date", ev.target.value)} className={e.received_date ? "border-destructive" : ""} /></TableCell>
                                        <TableCell><Input value={r.supplier_lot_number} onChange={(ev) => setCell(idx, "supplier_lot_number", ev.target.value)} /></TableCell>
                                        <TableCell><Input value={r.storage_location} onChange={(ev) => setCell(idx, "storage_location", ev.target.value)} /></TableCell>
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
