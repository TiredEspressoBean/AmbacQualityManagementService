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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useReceiveExpectedLot } from "@/hooks/useReceivingMutations";

type Props = {
    lotId: string;
    /** What the material is, for the dialog title — the placeholder lot number means
     *  nothing to the person holding the box. */
    itemName: string;
    /** Quantity ordered, prefilled so a matching delivery is one click. */
    orderedQuantity?: string | null;
    unitOfMeasure?: string | null;
    /** Jump to the receiving-inspection screen for this lot. Offered only when routing
     *  actually parked the lot for a disposition — a dock-to-stock lot has nothing to
     *  inspect, and a dead link there is worse than no link. */
    onInspect?: (lotId: string) => void;
    open: boolean;
    onOpenChange: (open: boolean) => void;
};

/** Statuses that mean "someone still has to make a call on this lot". */
const NEEDS_DISPOSITION = ["RECEIVED", "AWAITING_INSPECTION", "QUARANTINE"];

const today = () => new Date().toISOString().slice(0, 10);

/**
 * Book in an expected receipt that has physically arrived.
 *
 * Two things get corrected at this moment and nowhere else: the supplier's real lot
 * number replaces the generated placeholder, and the quantity becomes what actually
 * turned up. Short shipments and overages are normal, so the quantity is editable
 * rather than assumed.
 *
 * The lot lands at RECEIVED and is then routed like any other delivery — to incoming
 * inspection, or straight to stock when the material has no receiving step. Which of
 * those happens is the routing rule's call, so the copy here doesn't promise either.
 */
export function ReceiveExpectedLotDialog({
    lotId,
    itemName,
    orderedQuantity,
    unitOfMeasure,
    onInspect,
    open,
    onOpenChange,
}: Props) {
    const [lotNumber, setLotNumber] = useState("");
    const [quantity, setQuantity] = useState(orderedQuantity ?? "");
    const [receivedDate, setReceivedDate] = useState(today());
    const receive = useReceiveExpectedLot();

    const reset = () => {
        setLotNumber("");
        setQuantity(orderedQuantity ?? "");
        setReceivedDate(today());
    };

    const qtyValid = quantity !== "" && Number(quantity) > 0;
    const canSubmit = lotNumber.trim() !== "" && qtyValid && receivedDate !== "" && !receive.isPending;
    const short = qtyValid && orderedQuantity != null && Number(quantity) !== Number(orderedQuantity);

    const submit = () => {
        if (!canSubmit) return;
        receive.mutate(
            {
                id: lotId,
                lot_number: lotNumber.trim(),
                quantity,
                received_date: receivedDate,
            },
            {
                onSuccess: (data: unknown) => {
                    // The response is the lot *after* routing ran, so it says where the
                    // lot actually went — inspection, a soft hold, or straight to stock.
                    const status = (data as { status?: string })?.status;
                    const parked = status != null && NEEDS_DISPOSITION.includes(status);
                    toast.success(
                        parked
                            ? `Lot ${lotNumber.trim()} received — waiting on incoming inspection.`
                            : `Lot ${lotNumber.trim()} received and available.`,
                        parked && onInspect
                            ? { action: { label: "Inspect", onClick: () => onInspect(lotId) } }
                            : undefined,
                    );
                    reset();
                    onOpenChange(false);
                },
                onError: (err: unknown) => {
                    const detail =
                        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
                    toast.error(detail ?? "Could not receive the lot");
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
                    <DialogTitle>Receive · {itemName}</DialogTitle>
                    <DialogDescription>
                        Book in the delivery. The lot is then routed the same way any receipt
                        is &mdash; to incoming inspection, or straight to stock if this
                        material doesn&rsquo;t need one.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-2">
                    <div className="space-y-1.5">
                        <Label htmlFor="rel-lot">Supplier lot number</Label>
                        <Input
                            id="rel-lot"
                            className="font-mono"
                            placeholder="As printed on the packing slip / label"
                            value={lotNumber}
                            onChange={(e) => setLotNumber(e.target.value)}
                        />
                        <p className="text-xs text-muted-foreground">
                            Replaces the placeholder number the expectation was recorded under.
                        </p>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                            <Label htmlFor="rel-qty">
                                Quantity received{unitOfMeasure ? ` (${unitOfMeasure})` : ""}
                            </Label>
                            <Input
                                id="rel-qty"
                                type="number"
                                min="0"
                                step="any"
                                value={quantity}
                                onChange={(e) => setQuantity(e.target.value)}
                            />
                            {short && (
                                <p className="text-xs text-amber-600">
                                    Ordered {orderedQuantity} — booking in what actually arrived.
                                </p>
                            )}
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="rel-date">Received</Label>
                            <Input
                                id="rel-date"
                                type="date"
                                value={receivedDate}
                                onChange={(e) => setReceivedDate(e.target.value)}
                            />
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={receive.isPending}
                    >
                        Cancel
                    </Button>
                    <Button onClick={submit} disabled={!canSubmit}>
                        {receive.isPending ? "Receiving…" : "Receive lot"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
