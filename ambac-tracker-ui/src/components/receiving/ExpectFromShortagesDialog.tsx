import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import { useBulkExpectedReceipts } from "@/hooks/useReceivingMutations";
import type { SourceRow } from "@/hooks/useScheduling";

type Draft = {
    row: SourceRow;
    quantity: string;
    promised: string;
    supplier: string;
    line: string;
};

const addDays = (days: number) => {
    const d = new Date();
    d.setDate(d.getDate() + days);
    return d.toISOString().slice(0, 10);
};

/** What's short, or failing that the forecast shortfall — a buyer ticked the row to
 *  cover *something*. Whole units; the buyer rounds up to a pack size. */
const defaultQty = (r: SourceRow) =>
    String(r.qty_short > 0 ? r.qty_short : Math.ceil(r.forecast_short ?? 0) || 1);

/** Ordered today, it lands a lead time from now — the honest default for a promise
 *  the buyer hasn't heard yet. With no lead time on file, the need-by date. */
const defaultPromised = (r: SourceRow) =>
    r.lead_time_days != null ? addDays(r.lead_time_days) : (r.need_by ?? addDays(0));

type Props = {
    rows: SourceRow[];
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onDone: () => void;
};

/**
 * Raise expected receipts from shortages on the sourcing report — the buyer has just
 * placed the orders in the ERP and records here what's coming, without re-keying the
 * item, the quantity or the supplier. One PO number for the batch (usually one PO per
 * supplier), a line per row. All or nothing.
 */
export function ExpectFromShortagesDialog({ rows, open, onOpenChange, onDone }: Props) {
    const [drafts, setDrafts] = useState<Draft[]>([]);
    const [poNumber, setPoNumber] = useState("");
    const companies = useRetrieveCompanies({ ordering: "name", limit: 1000, is_supplier: true });
    const bulk = useBulkExpectedReceipts();

    useEffect(() => {
        if (!open) return;
        setPoNumber("");
        setDrafts(rows.map((r) => ({
            row: r,
            quantity: defaultQty(r),
            promised: defaultPromised(r),
            supplier: r.preferred_supplier_id ?? "",
            line: "",
        })));
    }, [open, rows]);

    const update = (i: number, patch: Partial<Draft>) =>
        setDrafts((ds) => ds.map((d, j) => (j === i ? { ...d, ...patch } : d)));

    const valid = drafts.length > 0 && drafts.every((d) => Number(d.quantity) > 0 && d.promised);

    const submit = () =>
        bulk.mutate(
            drafts.map((d) => ({
                ...(d.row.buy_kind === "MATERIAL"
                    ? { material: d.row.item_id }
                    : { material_type: d.row.item_id }),
                quantity: d.quantity,
                promised_date: d.promised,
                supplier: d.supplier || null,
                erp_po_number: poNumber.trim(),
                erp_po_line: d.line.trim(),
            })),
            {
                onSuccess: (lots) => {
                    toast.success(`${lots.length} expected receipt${lots.length === 1 ? "" : "s"} recorded — planning now counts them as incoming.`);
                    onDone();
                    onOpenChange(false);
                },
                onError: (err: unknown) => {
                    const detail = (err as { response?: { data?: { detail?: string } } })
                        ?.response?.data?.detail;
                    toast.error(detail ?? "Could not record the expected receipts — none were saved.");
                },
            },
        );

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
                <DialogHeader>
                    <DialogTitle>Expect deliveries</DialogTitle>
                    <DialogDescription>
                        Record what you&rsquo;ve ordered in the ERP so planning counts it as
                        incoming. Nothing is purchased here.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-1.5">
                    <Label htmlFor="efs-po">
                        PO number <span className="text-muted-foreground">(optional, applies to every row)</span>
                    </Label>
                    <Input id="efs-po" className="max-w-xs" placeholder="e.g. 4500123"
                        value={poNumber} onChange={(e) => setPoNumber(e.target.value)} />
                </div>

                <div className="space-y-3">
                    {drafts.map((d, i) => (
                        <div key={`${d.row.buy_kind}:${d.row.item_id}`} className="rounded-md border p-3">
                            <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
                                <div>
                                    <span className="font-medium">{d.row.material}</span>
                                    {d.row.part_number && (
                                        <span className="ml-2 font-mono text-xs text-muted-foreground">{d.row.part_number}</span>
                                    )}
                                </div>
                                <span className="text-xs text-muted-foreground">
                                    short {d.row.qty_short} {d.row.unit_of_measure}
                                </span>
                            </div>
                            <div className="grid grid-cols-2 gap-2 sm:grid-cols-[6rem_9rem_1fr_5rem]">
                                <div className="space-y-1">
                                    <Label className="text-xs" htmlFor={`efs-q-${i}`}>Qty</Label>
                                    <Input id={`efs-q-${i}`} type="number" min="0" step="any"
                                        value={d.quantity} onChange={(e) => update(i, { quantity: e.target.value })} />
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-xs" htmlFor={`efs-d-${i}`}>Promised</Label>
                                    <Input id={`efs-d-${i}`} type="date"
                                        value={d.promised} onChange={(e) => update(i, { promised: e.target.value })} />
                                </div>
                                <div className="col-span-2 space-y-1 sm:col-span-1">
                                    <Label className="text-xs">Supplier</Label>
                                    <Select value={d.supplier} onValueChange={(v) => update(i, { supplier: v })}>
                                        <SelectTrigger aria-label="Supplier">
                                            <SelectValue placeholder="Select a supplier" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {(companies.data?.results ?? []).map((c) => (
                                                <SelectItem key={String(c.id)} value={String(c.id)}>{c.name}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-xs" htmlFor={`efs-l-${i}`}>PO line</Label>
                                    <Input id={`efs-l-${i}`} value={d.line}
                                        onChange={(e) => update(i, { line: e.target.value })} />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={bulk.isPending}>
                        Cancel
                    </Button>
                    <Button onClick={submit} disabled={!valid || bulk.isPending}>
                        {bulk.isPending ? "Recording…" : `Record ${drafts.length} expected receipt${drafts.length === 1 ? "" : "s"}`}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
