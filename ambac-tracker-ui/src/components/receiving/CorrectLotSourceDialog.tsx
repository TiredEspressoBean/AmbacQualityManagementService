import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api/generated";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import { useMaterialOptions } from "@/hooks/useMaterials";

type Lot = {
    id: string; lot_number: string;
    supplier?: string | null; material?: string | null; material_type?: string | null;
    erp_po_number?: string | null; erp_po_line?: string | null;
};

const NONE = "__none__";

/**
 * A lot's supplier, item or PO line keyed wrong at receipt: correct it, with a reason,
 * while nothing has been taken from it — once used, the trace already names it
 * (Corrections #25). Each change and the reason are kept on the lot.
 */
export function CorrectLotSourceDialog({ lot, open, onOpenChange }: {
    lot: Lot; open: boolean; onOpenChange: (open: boolean) => void;
}) {
    const queryClient = useQueryClient();
    const companies = useRetrieveCompanies({ ordering: "name", limit: 1000, is_supplier: true });
    const materials = useMaterialOptions();
    const [supplier, setSupplier] = useState(lot.supplier ?? NONE);
    const [material, setMaterial] = useState(lot.material ?? NONE);
    const [po, setPo] = useState(lot.erp_po_number ?? "");
    const [line, setLine] = useState(lot.erp_po_line ?? "");
    const [reason, setReason] = useState("");

    const body: Record<string, string | null> = {};
    if ((supplier === NONE ? null : supplier) !== (lot.supplier ?? null)) body.supplier = supplier === NONE ? null : supplier;
    if (lot.material && material !== lot.material && material !== NONE) body.material = material;
    if (po !== (lot.erp_po_number ?? "")) body.erp_po_number = po;
    if (line !== (lot.erp_po_line ?? "")) body.erp_po_line = line;
    const changed = Object.keys(body).length > 0;

    const mut = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: () => api.api_MaterialLots_correct_source_create(
            { ...body, reason: reason.trim() }, { params: { id: lot.id } }),
        onSuccess: () => {
            queryClient.invalidateQueries();
            toast.success(`Lot ${lot.lot_number} — receipt details corrected`);
            setReason("");
            onOpenChange(false);
        },
        onError: (e: unknown) => toast.error(apiErrorMessage(e) ?? "Couldn't correct the receipt details"),
    });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Correct receipt details · {lot.lot_number}</DialogTitle>
                    <DialogDescription>
                        The supplier, item or PO line was keyed wrong. Correctable while nothing has been
                        used, split or adjusted. Each change and your reason are kept on the lot.
                    </DialogDescription>
                </DialogHeader>
                <div className="grid grid-cols-2 gap-3">
                    <div className="col-span-2 space-y-1.5">
                        <Label>Supplier</Label>
                        <Select value={supplier} onValueChange={setSupplier}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value={NONE}>No supplier</SelectItem>
                                {(companies.data?.results ?? []).map((c) => (
                                    <SelectItem key={String(c.id)} value={String(c.id)}>{c.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    {lot.material && (
                        <div className="col-span-2 space-y-1.5">
                            <Label>Material</Label>
                            <Select value={material} onValueChange={setMaterial}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {(materials.data?.results ?? []).map((m) => (
                                        <SelectItem key={String(m.id)} value={String(m.id)}>{m.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    )}
                    <div className="space-y-1.5">
                        <Label htmlFor="cls-po">ERP PO</Label>
                        <Input id="cls-po" value={po} onChange={(e) => setPo(e.target.value)} />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="cls-line">PO line</Label>
                        <Input id="cls-line" value={line} onChange={(e) => setLine(e.target.value)} />
                    </div>
                    <Textarea className="col-span-2" rows={2} value={reason} onChange={(e) => setReason(e.target.value)}
                        aria-label="Reason" placeholder="Why — e.g. the slip is PO 4471 line 3, not line 2" />
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={mut.isPending}>Cancel</Button>
                    <Button onClick={() => mut.mutate()} disabled={!changed || !reason.trim() || mut.isPending}>
                        {mut.isPending ? "Saving…" : "Correct"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
