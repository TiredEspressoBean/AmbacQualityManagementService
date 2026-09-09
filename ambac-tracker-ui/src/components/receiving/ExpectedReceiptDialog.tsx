import { useState } from "react";
import { toast } from "sonner";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useMaterialOptions } from "@/hooks/useMaterials";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import { useRecordExpectedReceipt } from "@/hooks/useReceivingMutations";

type Props = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
};

/**
 * Record stock that has been ordered but hasn't arrived.
 *
 * This is a planning signal, not a purchase order — purchasing lives in the ERP and
 * the PO number here is a reference back to it. Recording the expectation is what stops
 * the sourcing report asking for a second order of something already on a truck.
 *
 * The promised date is required rather than optional: material planning places incoming
 * stock in the month it lands, so an undated receipt would count as cover without ever
 * arriving anywhere on the plan.
 *
 * Supplier and promised date together are also what on-time-delivery scoring measures —
 * OTD is `received_date <= promised_date` across a supplier's dated lots, so an
 * expectation recorded here becomes a real OTD data point the moment it's booked in.
 * Leaving the supplier blank silently opts that delivery out of the scorecard.
 */
export function ExpectedReceiptDialog({ open, onOpenChange }: Props) {
    const [material, setMaterial] = useState("");
    const [quantity, setQuantity] = useState("");
    const [promisedDate, setPromisedDate] = useState("");
    const [supplier, setSupplier] = useState("");
    const [poNumber, setPoNumber] = useState("");

    const materials = useMaterialOptions();
    const companies = useRetrieveCompanies({ ordering: "name", limit: 1000 } as never);
    const record = useRecordExpectedReceipt();

    /** Picking a material pre-selects its preferred supplier — the common case is buying
     *  from the usual source, and a second-source order just overrides it. */
    const chooseMaterial = (id: string) => {
        setMaterial(id);
        const m = materials.data?.results?.find((x) => String(x.id) === id);
        const preferred = m?.preferred_supplier;
        if (preferred) setSupplier(String(preferred));
    };

    const reset = () => {
        setMaterial("");
        setQuantity("");
        setPromisedDate("");
        setSupplier("");
        setPoNumber("");
    };

    const qtyValid = quantity !== "" && Number(quantity) > 0;
    const canSubmit = material !== "" && qtyValid && promisedDate !== "" && !record.isPending;

    const submit = () => {
        if (!canSubmit) return;
        record.mutate(
            {
                material,
                quantity,
                promised_date: promisedDate,
                supplier: supplier || null,
                erp_po_number: poNumber.trim(),
            },
            {
                onSuccess: () => {
                    toast.success("Expected receipt recorded — planning now counts it as incoming.");
                    reset();
                    onOpenChange(false);
                },
                onError: (err: unknown) => {
                    const detail =
                        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
                    toast.error(detail ?? "Could not record the expected receipt");
                },
            },
        );
    };

    return (
        <Dialog
            open={open}
            onOpenChange={(o) => {
                if (!o) reset();
                onOpenChange(o);
            }}
        >
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Expect a delivery</DialogTitle>
                    <DialogDescription>
                        Record material that&rsquo;s on order but hasn&rsquo;t arrived, so planning
                        counts it as incoming supply. It stays out of stock and can&rsquo;t be
                        picked until it&rsquo;s booked in at receiving.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-2">
                    <div className="space-y-1.5">
                        <Label htmlFor="er-material">Material</Label>
                        <Select value={material} onValueChange={chooseMaterial}>
                            <SelectTrigger id="er-material">
                                <SelectValue
                                    placeholder={
                                        materials.isLoading ? "Loading…" : "Select a material"
                                    }
                                />
                            </SelectTrigger>
                            <SelectContent>
                                {(materials.data?.results ?? []).map((m) => (
                                    <SelectItem key={String(m.id)} value={String(m.id)}>
                                        {m.name}
                                        {m.part_number ? ` · ${m.part_number}` : ""}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                            <Label htmlFor="er-qty">Quantity</Label>
                            <Input
                                id="er-qty"
                                type="number"
                                min="0"
                                step="any"
                                value={quantity}
                                onChange={(e) => setQuantity(e.target.value)}
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="er-date">Promised delivery</Label>
                            <Input
                                id="er-date"
                                type="date"
                                value={promisedDate}
                                onChange={(e) => setPromisedDate(e.target.value)}
                            />
                        </div>
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="er-supplier">Supplier</Label>
                        <Select value={supplier} onValueChange={setSupplier}>
                            <SelectTrigger id="er-supplier">
                                <SelectValue
                                    placeholder={
                                        companies.isLoading ? "Loading…" : "Select a supplier"
                                    }
                                />
                            </SelectTrigger>
                            <SelectContent>
                                {(companies.data?.results ?? []).map((c) => (
                                    <SelectItem key={String(c.id)} value={String(c.id)}>
                                        {c.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <p className="text-xs text-muted-foreground">
                            {supplier
                                ? "On-time delivery is scored against the promised date above when this lands."
                                : "Without a supplier this delivery won’t count toward anyone’s on-time-delivery score."}
                        </p>
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="er-po">
                            PO reference <span className="text-muted-foreground">(optional)</span>
                        </Label>
                        <Input
                            id="er-po"
                            placeholder="e.g. PO-4471"
                            value={poNumber}
                            onChange={(e) => setPoNumber(e.target.value)}
                        />
                        <p className="text-xs text-muted-foreground">
                            Points back at the order in your ERP, and names the placeholder lot
                            until the supplier&rsquo;s real lot number arrives with the goods.
                        </p>
                    </div>
                </div>

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={record.isPending}
                    >
                        Cancel
                    </Button>
                    <Button onClick={submit} disabled={!canSubmit}>
                        {record.isPending ? "Recording…" : "Record expected receipt"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
