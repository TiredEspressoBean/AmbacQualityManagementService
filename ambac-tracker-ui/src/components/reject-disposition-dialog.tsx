import { useEffect, useState } from "react";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

/** Disposition types relevant to rejected purchased material (subset of the
 *  full DispositionTypeEnum — REPAIR is AS9100-rework-centric, not receiving). */
const DISPOSITION_TYPES = [
    { value: "RETURN_TO_SUPPLIER", label: "Return to supplier" },
    { value: "SCRAP", label: "Scrap" },
    { value: "USE_AS_IS", label: "Use as is (MRB)" },
    { value: "REWORK", label: "Rework" },
] as const;

const SEVERITIES = [
    { value: "CRITICAL", label: "Critical — safety / regulatory" },
    { value: "MAJOR", label: "Major — functional" },
    { value: "MINOR", label: "Minor — cosmetic" },
] as const;

export type RejectDispositionValues = {
    disposition_type: string;
    severity: string;
    description: string;
    quantity_affected: number;
    raise_scar: boolean;
};

export function RejectDispositionDialog({
    open, onOpenChange, lotNumber, supplierName, hasSupplier, quantity, defectives, sampleSize, acceptNumber,
    defectBreakdown, submitting, onConfirm,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    lotNumber: string;
    supplierName?: string | null;
    hasSupplier: boolean;
    quantity: number;
    /** Inspection context, used to pre-fill the nonconformance summary. */
    defectives?: number;
    sampleSize?: number;
    acceptNumber?: number;
    /** Defect tally by RIP characteristic, e.g. "Outer Diameter: 2, Visual: 1". */
    defectBreakdown?: string;
    submitting?: boolean;
    onConfirm: (values: RejectDispositionValues) => void;
}) {
    const prefill =
        (defectives != null && sampleSize != null
            ? `Rejected at receiving inspection: ${defectives} defective of ${sampleSize} inspected (accept ≤ ${acceptNumber ?? 0}).`
            : "Rejected at receiving inspection.")
        + (defectBreakdown ? ` Defects — ${defectBreakdown}.` : "");

    const [dispositionType, setDispositionType] = useState<string>("RETURN_TO_SUPPLIER");
    const [severity, setSeverity] = useState<string>("MAJOR");
    const [description, setDescription] = useState<string>(prefill);
    const [raiseScar, setRaiseScar] = useState<boolean>(hasSupplier);

    // The dialog stays mounted (open toggles visibility), so useState initializers
    // would freeze stale props — notably sample size before the plan query resolves.
    // Re-seed from current props each time it opens.
    useEffect(() => {
        if (!open) return;
        setDispositionType("RETURN_TO_SUPPLIER");
        setSeverity("MAJOR");
        setDescription(prefill);
        setRaiseScar(hasSupplier);
        // eslint-disable-next-line react-hooks/exhaustive-deps -- re-seed only on open transition
    }, [open]);

    const isRTV = dispositionType === "RETURN_TO_SUPPLIER";

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>Reject lot <span className="font-mono">{lotNumber}</span></DialogTitle>
                    <DialogDescription>
                        Rejecting opens a nonconformance (disposition) so the material has a defined
                        outcome — it isn't just marked rejected.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-1">
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                            <Label>What happens to it?</Label>
                            <Select value={dispositionType} onValueChange={setDispositionType}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {DISPOSITION_TYPES.map((d) => (
                                        <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5">
                            <Label>Severity</Label>
                            <Select value={severity} onValueChange={setSeverity}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {SEVERITIES.map((s) => (
                                        <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="rounded-md border bg-muted/40 p-3 text-sm space-y-1">
                        <div>Rejecting the <b>whole lot</b> — <b>{quantity}</b> units affected.</div>
                        {defectives != null && sampleSize != null && (
                            <div className="text-xs text-muted-foreground">
                                {defectives} defective found in the sample of {sampleSize} (accept ≤ {acceptNumber ?? 0}).
                            </div>
                        )}
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="rd-desc">Nonconformance</Label>
                        <Textarea
                            id="rd-desc"
                            rows={3}
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                        />
                    </div>

                    {isRTV && (
                        <div className="rounded-md border bg-muted/40 p-3 space-y-2">
                            <p className="text-sm">
                                Return to <b>{supplierName ?? "supplier"}</b>.
                            </p>
                            <label className="flex items-center gap-2 text-sm">
                                <Checkbox
                                    checked={raiseScar}
                                    onCheckedChange={(c) => setRaiseScar(c === true)}
                                    disabled={!hasSupplier}
                                />
                                Open a SCAR against the supplier
                            </label>
                            {!hasSupplier && (
                                <p className="text-xs text-muted-foreground">No supplier on this lot — can't raise a SCAR.</p>
                            )}
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>Cancel</Button>
                    <Button
                        variant="destructive"
                        disabled={submitting}
                        onClick={() =>
                            onConfirm({
                                disposition_type: dispositionType,
                                severity,
                                description,
                                // Derived from receiving: a sampling reject rejects the whole lot.
                                quantity_affected: quantity ?? 0,
                                raise_scar: isRTV && raiseScar && hasSupplier,
                            })
                        }
                    >
                        {submitting ? "Rejecting…" : "Reject & open disposition"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
