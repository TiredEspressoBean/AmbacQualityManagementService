import { useState } from "react";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useReportEmail } from "@/hooks/useReportEmail";
import { useRejectRemainder, useShipBack } from "@/hooks/useReceivingMutations";

const errorOf = (err: unknown, fallback: string) =>
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback;

type Base = { lotId: string; lotNumber: string; open: boolean; onOpenChange: (o: boolean) => void };

/**
 * The dock ships rejected material back to the supplier. Print the RTV sheet to go with
 * it, record the carrier or the supplier's RMA, and the lot leaves stock as Returned —
 * not scrapped: the goods exist, at the vendor. Credit is settled in the ERP.
 */
export function ShipBackDialog({ lotId, lotNumber, supplierName, open, onOpenChange }: Base & {
    supplierName?: string | null;
}) {
    const [note, setNote] = useState("");
    const [rma, setRma] = useState("");
    const [replacement, setReplacement] = useState(false);
    const [replacementDate, setReplacementDate] = useState("");
    const ship = useShipBack();
    const { downloadReport } = useReportEmail();
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Ship back · {lotNumber}</DialogTitle>
                    <DialogDescription>
                        Returning to {supplierName ?? "the supplier"}. Send the RTV sheet with the
                        goods. Any credit is settled in your ERP.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-3 py-1">
                    <div className="space-y-1.5">
                        <Label htmlFor="sb-rma">Supplier&rsquo;s RMA number <span className="text-muted-foreground">(if they gave one)</span></Label>
                        <Input id="sb-rma" value={rma} onChange={(e) => setRma(e.target.value)} />
                    </div>
                    <Button variant="outline" size="sm"
                        onClick={() => void downloadReport("rtv_sheet", { lot_id: lotId, rma_number: rma })}>
                        Print RTV sheet
                    </Button>
                    <div className="space-y-1.5">
                        <Label htmlFor="sb-note">Carrier or tracking <span className="text-muted-foreground">(optional)</span></Label>
                        <Input id="sb-note" value={note} onChange={(e) => setNote(e.target.value)} />
                    </div>
                    <label className="flex items-center gap-2 text-sm">
                        <Checkbox checked={replacement} onCheckedChange={(v) => setReplacement(!!v)} />
                        The supplier is sending replacements
                    </label>
                    {replacement && (
                        <div className="space-y-1.5">
                            <Label htmlFor="sb-rep">Replacements promised for</Label>
                            <Input id="sb-rep" type="date" value={replacementDate} onChange={(e) => setReplacementDate(e.target.value)} />
                            <p className="text-xs text-muted-foreground">Adds an expected delivery for the same quantity, so planning sees it and it can be chased.</p>
                        </div>
                    )}
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={ship.isPending}>Cancel</Button>
                    <Button disabled={ship.isPending || (replacement && !replacementDate)}
                        onClick={() => ship.mutate({ id: lotId, note, rma_number: rma, replacement_promised_date: replacement ? replacementDate : null }, {
                            onSuccess: () => { toast.success(`Lot ${lotNumber} shipped back to the supplier.`); onOpenChange(false); },
                            onError: (e) => toast.error(errorOf(e, "Could not mark the lot shipped back")),
                        })}>
                        {ship.isPending ? "Saving…" : "Mark shipped back"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

/**
 * Escalate a partial reject to the whole lot after the fact — reject what is left of a
 * lot already accepted. What has been used stays used; the record shows it.
 */
export function RejectRemainderDialog({ lotId, lotNumber, remaining, unitOfMeasure, open, onOpenChange }: Base & {
    remaining?: string | null;
    unitOfMeasure?: string | null;
}) {
    const [type, setType] = useState<"RETURN_TO_SUPPLIER" | "SCRAP">("RETURN_TO_SUPPLIER");
    const [reason, setReason] = useState("");
    const reject = useRejectRemainder();
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Reject remaining stock · {lotNumber}</DialogTitle>
                    <DialogDescription>
                        Rejects the {remaining ?? "remaining"} {unitOfMeasure ?? ""} still on hand and opens a
                        disposition. Anything already used is not reversed.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-3 py-1">
                    <div className="space-y-1.5">
                        <Label>What happens to it?</Label>
                        <Select value={type} onValueChange={(v) => setType(v as typeof type)}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="RETURN_TO_SUPPLIER">Return to supplier</SelectItem>
                                <SelectItem value="SCRAP">Scrap</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="rr-reason">Why</Label>
                        <Textarea id="rr-reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)}
                            placeholder="e.g. Field failures traced to this lot — rejecting the remainder" />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={reject.isPending}>Cancel</Button>
                    <Button variant="destructive" disabled={!reason.trim() || reject.isPending}
                        onClick={() => reject.mutate({ id: lotId, disposition_type: type, description: reason.trim() }, {
                            onSuccess: () => { toast.success(`Rest of lot ${lotNumber} rejected · disposition opened`); onOpenChange(false); },
                            onError: (e) => toast.error(errorOf(e, "Could not reject the remainder")),
                        })}>
                        {reject.isPending ? "Rejecting…" : "Reject remaining stock"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
