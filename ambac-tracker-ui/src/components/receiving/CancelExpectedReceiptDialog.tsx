import { useState } from "react";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCancelExpectedReceipt } from "@/hooks/useReceivingMutations";

type Props = {
    lotId: string;
    /** What's expected, for the title — "PO 4410 / 2 · Seal". */
    label: string;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCancelled?: () => void;
};

/**
 * An expected receipt that won't come — the ERP cancelled the line, or a sheet typed
 * before the ERP caught up expected a line already received. It stops counting as
 * supply and drops off Late deliveries; the reason stays on the lot's record.
 */
export function CancelExpectedReceiptDialog({ lotId, label, open, onOpenChange, onCancelled }: Props) {
    const [reason, setReason] = useState("");
    const cancel = useCancelExpectedReceipt();

    const submit = () =>
        cancel.mutate({ id: lotId, reason: reason.trim() }, {
            onSuccess: () => {
                toast.success(`${label}: no longer expected.`);
                onCancelled?.();
                onOpenChange(false);
            },
            onError: (err: unknown) => {
                const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
                toast.error(detail ?? "Could not cancel the expected receipt");
            },
        });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Cancel expected receipt · {label}</DialogTitle>
                    <DialogDescription>
                        It stops counting as incoming supply and leaves Late deliveries. The PO line
                        itself is the ERP&rsquo;s — if the ERP still shows it open, the next
                        expected-receipts sheet will expect it again, and say so.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-1.5 py-2">
                    <Label htmlFor="cxl-reason">Reason</Label>
                    <Textarea id="cxl-reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)}
                        placeholder="e.g. Already received on the 28th — the ERP hadn't caught up" />
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={cancel.isPending}>Keep it</Button>
                    <Button variant="destructive" onClick={submit} disabled={!reason.trim() || cancel.isPending}>
                        {cancel.isPending ? "Cancelling…" : "Cancel expected receipt"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
