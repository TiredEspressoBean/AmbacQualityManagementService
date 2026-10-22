import { useState } from "react";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAdjustLotQuantity, useCorrectReceipt } from "@/hooks/useReceivingMutations";
import { apiErrorMessage } from "@/lib/api/describeApiError";

type Props = {
    lotId: string;
    lotNumber: string;
    remaining: string | null | undefined;
    unitOfMeasure?: string | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    /** "correct": fix the quantity RECEIVED (a mis-keyed receipt); `remaining` is then
     *  the received figure. Default "adjust": what's left now (shrinkage). */
    mode?: "adjust" | "correct";
};

/**
 * Correct what's left of a lot to what's physically there — counted 1,940, not 2,000; a
 * box crushed in the rack. UQMES isn't the stock register (the ERP is), but planning nets
 * against this figure, so a wrong one must be fixable — with a reason on record.
 */
export function AdjustLotQuantityDialog({ lotId, lotNumber, remaining, unitOfMeasure, open, onOpenChange, mode = "adjust" }: Props) {
    const correcting = mode === "correct";
    const [quantity, setQuantity] = useState(remaining ?? "");
    const [reason, setReason] = useState("");
    const adjustMut = useAdjustLotQuantity();
    const correctMut = useCorrectReceipt();
    const adjust = correcting ? correctMut : adjustMut;

    const valid = quantity !== "" && (correcting ? Number(quantity) > 0 : Number(quantity) >= 0) && reason.trim() !== "";
    const delta = quantity !== "" && remaining != null ? Number(quantity) - Number(remaining) : 0;

    const submit = () =>
        adjust.mutate({ id: lotId, quantity, reason: reason.trim() }, {
            onSuccess: () => {
                toast.success(`Lot ${lotNumber} ${correcting ? "receipt corrected" : "adjusted"} to ${quantity}${unitOfMeasure ? ` ${unitOfMeasure}` : ""}.`);
                onOpenChange(false);
            },
            onError: (err: unknown) => {
                const detail = apiErrorMessage(err);
                toast.error(detail ?? "Could not adjust the lot");
            },
        });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{correcting ? "Correct receipt" : "Adjust quantity"} · {lotNumber}</DialogTitle>
                    <DialogDescription>
                        {correcting ? (
                            <>The quantity received was keyed wrong. This changes the receipt itself,
                            and what&rsquo;s on hand with it; the change and its reason are kept on the
                            lot&rsquo;s record. If the receipt was already posted, the receipts sheet
                            flags it &ldquo;Changed since posted&rdquo; so the ERP is corrected too.</>
                        ) : (
                            <>Set what&rsquo;s actually on hand (shrinkage, a recount). The change and its
                            reason are kept on the lot&rsquo;s record. Adjust the ERP&rsquo;s figure there too.</>
                        )}
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div className="space-y-1.5">
                        <Label htmlFor="adj-qty">
                            {correcting ? "Actually received" : "On hand now"}{unitOfMeasure ? ` (${unitOfMeasure})` : ""}
                        </Label>
                        <Input id="adj-qty" type="number" min="0" step="any"
                            value={quantity} onChange={(e) => setQuantity(e.target.value)} />
                        {remaining != null && delta !== 0 && (
                            <p className="text-xs text-muted-foreground">
                                Was {remaining} — {delta > 0 ? "+" : ""}{delta}
                            </p>
                        )}
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="adj-reason">Reason</Label>
                        <Textarea id="adj-reason" rows={2} placeholder="e.g. Recount — 60 short; two sleeves damaged"
                            value={reason} onChange={(e) => setReason(e.target.value)} />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={adjust.isPending}>Cancel</Button>
                    <Button onClick={submit} disabled={!valid || adjust.isPending}>
                        {adjust.isPending ? "Saving…" : correcting ? "Correct receipt" : "Adjust"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
