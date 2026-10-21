/** Clearing a work-order hold: restates why it stopped and records what resolved it.
 *  The note is required for Quality and Tooling holds (the server refuses those without
 *  one) and optional for the rest. */
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { holdReasonLabel, type WorkOrderHold } from "./WorkOrderHoldBanner";

export const NEEDS_RESOLUTION = new Set(["QUALITY", "TOOLING"]);

export function ClearHoldDialog({ open, onOpenChange, hold, count, pending, onConfirm }: {
    open: boolean;
    onOpenChange: (o: boolean) => void;
    /** The hold being cleared; omit for a bulk clear of several. */
    hold?: WorkOrderHold | null;
    /** How many work orders a bulk clear covers. */
    count?: number;
    pending?: boolean;
    onConfirm: (notes: string) => void;
}) {
    const [notes, setNotes] = useState("");
    const required = !!hold && NEEDS_RESOLUTION.has(hold.reason);
    const close = (o: boolean) => { onOpenChange(o); if (!o) setNotes(""); };
    return (
        <Dialog open={open} onOpenChange={close}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>
                        {count && count > 1 ? `Clear ${count} holds and resume?` : "Clear the hold and resume?"}
                    </DialogTitle>
                    <DialogDescription>
                        {hold
                            ? `On hold for ${holdReasonLabel(hold.reason)}${hold.notes ? ` — ${hold.notes}` : ""}${
                                hold.placed_by_name ? `, placed by ${hold.placed_by_name}` : ""}. `
                            : "Quality and Tooling holds need a resolution note; any without one stay on hold. "}
                        Work can start again once it's cleared.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-1.5">
                    <Label htmlFor="clear-hold-notes">
                        What resolved it{required ? " *" : " (optional)"}
                    </Label>
                    <Textarea id="clear-hold-notes" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)}
                              placeholder="e.g. Gauge recalibrated and verified; suspect parts re-inspected, all in spec." />
                </div>
                <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => close(false)}>Keep on hold</Button>
                    <Button type="button" disabled={pending || (required && !notes.trim())}
                            onClick={() => onConfirm(notes.trim())}>
                        {pending ? "Clearing…" : "Clear hold"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
