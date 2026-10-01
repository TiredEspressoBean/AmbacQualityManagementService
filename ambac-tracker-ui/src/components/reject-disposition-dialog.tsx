import { useEffect, useState } from "react";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";

/** Where rejected purchased material goes, decided at rejection. Use-as-is is a later,
 *  separately authorized concession on the disposition; rework isn't for bought stock. */
const DISPOSITION_TYPES = [
    { value: "RETURN_TO_SUPPLIER", label: "Return to supplier" },
    { value: "SCRAP", label: "Scrap" },
] as const;

const SEVERITIES = [
    { value: "CRITICAL", label: "Critical — safety / regulatory" },
    { value: "MAJOR", label: "Major — functional" },
    { value: "MINOR", label: "Minor — cosmetic" },
] as const;

export type RejectDispositionValues = {
    disposition_type: "RETURN_TO_SUPPLIER" | "SCRAP";
    severity: "CRITICAL" | "MAJOR" | "MINOR";
    description: string;
    /** Pieces found bad, when only part of the lot is rejected; null with `whole_lot`. */
    rejected_quantity: string | null;
    whole_lot: boolean;
    raise_scar: boolean;
};

export function RejectDispositionDialog({
    open, onOpenChange, lotNumber, supplierName, hasSupplier, canRaiseScar = true, quantity, defectives, sampleSize, acceptNumber,
    defectBreakdown, submitting, onConfirm, canRejectWholeLot = false, unitOfMeasure,
}: {
    /** Holds `reject_whole_lot`. Without it a whole-lot reject is sent to QA as a request. */
    canRejectWholeLot?: boolean;
    unitOfMeasure?: string | null;
    open: boolean;
    onOpenChange: (v: boolean) => void;
    lotNumber: string;
    supplierName?: string | null;
    hasSupplier: boolean;
    /** Whether the current user holds `initiate_capa`. A SCAR is a
     *  supplier-tagged CAPA, so raise_scar is gated the same as any other
     *  CAPA initiation. False → offer the reject without the SCAR option
     *  rather than let it fail silently server-side. */
    canRaiseScar?: boolean;
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

    const [dispositionType, setDispositionType] = useState<RejectDispositionValues["disposition_type"]>("RETURN_TO_SUPPLIER");
    const [severity, setSeverity] = useState<RejectDispositionValues["severity"]>("MAJOR");
    const [description, setDescription] = useState<string>(prefill);
    const [raiseScar, setRaiseScar] = useState<boolean>(hasSupplier);
    const [scope, setScope] = useState<"PART" | "WHOLE">("PART");
    const [badQty, setBadQty] = useState("");

    // The dialog stays mounted (open toggles visibility), so useState initializers
    // would freeze stale props — notably sample size before the plan query resolves.
    // Re-seed from current props each time it opens.
    useEffect(() => {
        if (!open) return;
        setDispositionType("RETURN_TO_SUPPLIER");
        setSeverity("MAJOR");
        setDescription(prefill);
        setRaiseScar(hasSupplier);
        setScope("PART");
        setBadQty("");
        // eslint-disable-next-line react-hooks/exhaustive-deps -- re-seed only on open transition
    }, [open]);

    const isRTV = dispositionType === "RETURN_TO_SUPPLIER";
    const badValid = badQty !== "" && Number(badQty) > 0 && Number(badQty) < quantity;
    const canSubmit = !submitting && (scope === "WHOLE" || badValid);
    const unit = unitOfMeasure ?? "";

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
                            <Select value={dispositionType} onValueChange={(v) => setDispositionType(v as RejectDispositionValues["disposition_type"])}>
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
                            <Select value={severity} onValueChange={(v) => setSeverity(v as RejectDispositionValues["severity"])}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {SEVERITIES.map((s) => (
                                        <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <fieldset className="space-y-2 rounded-md border p-3 text-sm">
                        <legend className="px-1 font-medium">Which pieces?</legend>
                        {defectives != null && sampleSize != null && (
                            <p className="text-xs text-muted-foreground">
                                {defectives} defective found in the sample of {sampleSize} (accept ≤ {acceptNumber ?? 0}).
                            </p>
                        )}
                        <label className="flex items-start gap-2">
                            <input type="radio" name="rd-scope" className="mt-1" checked={scope === "PART"}
                                onChange={() => setScope("PART")} />
                            <span className="flex-1">
                                <span className="font-medium">Some of them</span> — these are bad, accept the rest
                                {scope === "PART" && (
                                    <span className="mt-1.5 flex items-center gap-2">
                                        <Input className="w-28" type="number" min="0" step="any" aria-label="Pieces rejected"
                                            value={badQty} onChange={(e) => setBadQty(e.target.value)} />
                                        <span className="text-muted-foreground">of {quantity} {unit} rejected</span>
                                    </span>
                                )}
                                {scope === "PART" && badQty !== "" && !badValid && (
                                    <span className="block text-xs text-destructive">
                                        Fewer than the whole lot — to reject all of it, choose the whole lot.
                                    </span>
                                )}
                            </span>
                        </label>
                        <label className="flex items-start gap-2">
                            <input type="radio" name="rd-scope" className="mt-1" checked={scope === "WHOLE"}
                                onChange={() => setScope("WHOLE")} />
                            <span>
                                <span className="font-medium">Reject whole lot</span> — all {quantity} {unit}
                                {scope === "WHOLE" && !canRejectWholeLot && (
                                    <span className="block text-xs text-amber-700">
                                        This goes to QA as a request: the lot is held until someone who may reject
                                        a whole lot confirms it, or releases it for a partial reject.
                                    </span>
                                )}
                            </span>
                        </label>
                    </fieldset>

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
                                    checked={raiseScar && canRaiseScar}
                                    onCheckedChange={(c) => setRaiseScar(c === true)}
                                    disabled={!hasSupplier || !canRaiseScar}
                                />
                                Open a SCAR against the supplier
                            </label>
                            {!hasSupplier && (
                                <p className="text-xs text-muted-foreground">No supplier on this lot — can't raise a SCAR.</p>
                            )}
                            {hasSupplier && !canRaiseScar && (
                                <p className="text-xs text-muted-foreground">
                                    You don't have permission to raise a SCAR (needs
                                    <b> initiate_capa</b>). Reject the lot and ask QA to
                                    raise it.
                                </p>
                            )}
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>Cancel</Button>
                    <Button
                        variant="destructive"
                        disabled={!canSubmit}
                        onClick={() =>
                            onConfirm({
                                disposition_type: dispositionType,
                                severity,
                                description,
                                rejected_quantity: scope === "PART" ? badQty : null,
                                whole_lot: scope === "WHOLE",
                                raise_scar: isRTV && raiseScar && hasSupplier && canRaiseScar,
                            })
                        }
                    >
                        {submitting ? "Rejecting…"
                            : scope === "WHOLE" && !canRejectWholeLot ? "Request whole-lot reject"
                            : "Reject & open disposition"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
