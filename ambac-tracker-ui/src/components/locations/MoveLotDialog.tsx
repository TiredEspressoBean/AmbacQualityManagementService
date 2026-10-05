import { useState } from "react";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LocationInput } from "@/components/locations/LocationInput";
import { useMoveLot } from "@/hooks/useLocations";

const errorOf = (err: unknown, fallback: string) =>
    (err as { response?: { data?: { detail?: string; to?: string[] } } })?.response?.data?.detail ?? fallback;

/**
 * Move a lot — all of it, or some of it (split off first; the rest stays put). The
 * move is recorded: from where, to where, who, when.
 */
export function MoveLotDialog({ lot, open, onOpenChange }: {
    lot: { id: string; lot_number: string; storage_location?: string | null;
           quantity_remaining?: string | number | null; unit_of_measure?: string | null };
    open: boolean;
    onOpenChange: (o: boolean) => void;
}) {
    const move = useMoveLot();
    const [to, setTo] = useState("");
    const [qty, setQty] = useState("");
    const remaining = lot.quantity_remaining != null ? Number(lot.quantity_remaining) : null;
    const partial = qty !== "" && remaining != null && Number(qty) < remaining;

    const submit = () => {
        if (!to.trim()) return;
        move.mutate({ id: lot.id, to, quantity: qty || null }, {
            onSuccess: (moved) => {
                toast.success(partial
                    ? `${qty} ${lot.unit_of_measure ?? ""} split off as ${moved.lot_number} and moved to ${moved.storage_location}.`
                    : `Lot ${lot.lot_number} moved to ${moved.storage_location}.`);
                setTo(""); setQty("");
                onOpenChange(false);
            },
            onError: (e) => toast.error(errorOf(e, "Could not move the lot")),
        });
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Move · {lot.lot_number}</DialogTitle>
                    <DialogDescription>
                        Now in {lot.storage_location || "no location"}. Scan the destination&rsquo;s label or type it.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-3 py-1">
                    <div className="space-y-1.5">
                        <Label htmlFor="mv-to">To</Label>
                        <LocationInput id="mv-to" value={to} onChange={setTo} onEnter={submit} autoFocus />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="mv-qty">
                            Quantity <span className="text-muted-foreground">(blank moves all{remaining != null ? ` ${remaining} ${lot.unit_of_measure ?? ""}` : ""})</span>
                        </Label>
                        <Input id="mv-qty" type="number" min={0} value={qty} onChange={(e) => setQty(e.target.value)} />
                        {partial && <p className="text-xs text-muted-foreground">Splits {qty} off into a new lot; the rest stays where it is.</p>}
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={move.isPending}>Cancel</Button>
                    <Button onClick={submit} disabled={move.isPending || !to.trim()}>{move.isPending ? "Moving…" : "Move"}</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
