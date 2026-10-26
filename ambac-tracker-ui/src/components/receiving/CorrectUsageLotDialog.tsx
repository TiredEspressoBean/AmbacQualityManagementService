import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api/generated";
import { apiErrorMessage } from "@/lib/api/describeApiError";

type Props = {
    usageId: string;
    /** The lot the draw is recorded against now — the wrong one. */
    lotId: string;
    lotNumber: string;
    quantity: number;
    unitOfMeasure?: string | null;
    /** The item, to offer only lots of the same thing. */
    materialId?: string | null;
    materialTypeId?: string | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
};

/**
 * A draw recorded against the wrong lot: point it at the lot actually used. The wrong
 * lot gets its quantity back and the right one is drawn, so the recall trace names the
 * lot that really went in. The change and its reason are kept on the record.
 */
export function CorrectUsageLotDialog({
    usageId, lotId, lotNumber, quantity, unitOfMeasure, materialId, materialTypeId, open, onOpenChange,
}: Props) {
    const queryClient = useQueryClient();
    const [newLot, setNewLot] = useState("");
    const [reason, setReason] = useState("");

    const { data: lots } = useQuery({
        queryKey: ["material-lots", "same-item", materialId, materialTypeId],
        enabled: open,
        queryFn: () => api.api_MaterialLots_list({
            queries: {
                ...(materialId ? { material: materialId } : {}),
                ...(materialTypeId ? { material_type: materialTypeId } : {}),
                limit: 200,
            },
        }),
    });
    const candidates = (lots?.results ?? []).filter((l) =>
        String(l.id) !== lotId && (l.status === "ACCEPTED" || l.status === "IN_USE")
        && Number(l.quantity_remaining ?? 0) >= quantity);

    const mut = useMutation({
        mutationFn: () => api.api_MaterialUsages_correct_lot_create(
            { lot: newLot, reason: reason.trim() }, { params: { id: usageId } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "material-lot" || q.queryKey[0] === "material-lots" });
            const to = candidates.find((l) => String(l.id) === newLot)?.lot_number ?? "the right lot";
            toast.success(`Draw moved from ${lotNumber} to ${to}.`);
            setNewLot("");
            setReason("");
            onOpenChange(false);
        },
        onError: (err: unknown) => toast.error(apiErrorMessage(err) ?? "Could not correct the lot"),
    });

    const valid = newLot !== "" && reason.trim() !== "";
    const unit = unitOfMeasure ? ` ${unitOfMeasure}` : "";

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Wrong lot · {lotNumber}</DialogTitle>
                    <DialogDescription>
                        This draw of {quantity}{unit} is recorded against {lotNumber}, but it came from
                        another lot. {lotNumber} gets the {quantity}{unit} back and the lot you pick is
                        drawn instead. The change and its reason are kept on the record.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div className="space-y-1.5">
                        <Label>Lot actually used</Label>
                        <Select value={newLot || undefined} onValueChange={setNewLot}>
                            <SelectTrigger><SelectValue placeholder="Choose a lot" /></SelectTrigger>
                            <SelectContent>
                                {candidates.map((l) => (
                                    <SelectItem key={String(l.id)} value={String(l.id)}>
                                        {l.lot_number} · {l.quantity_remaining}{unit} left
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        {lots && candidates.length === 0 && (
                            <p className="text-xs text-muted-foreground">
                                No other lot of this item has {quantity}{unit} in stock.
                            </p>
                        )}
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="cul-reason">Reason</Label>
                        <Textarea id="cul-reason" rows={2} placeholder="e.g. Picked from the next bin; label checked at the bench"
                            value={reason} onChange={(e) => setReason(e.target.value)} />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={mut.isPending}>Cancel</Button>
                    <Button onClick={() => mut.mutate()} disabled={!valid || mut.isPending}>
                        {mut.isPending ? "Saving…" : "Move the draw"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
