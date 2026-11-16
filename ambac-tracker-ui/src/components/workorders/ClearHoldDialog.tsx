/** Clearing a work-order hold: restates why it stopped and records what resolved it.
 *  The note is required for Quality and Tooling holds (the server refuses those without
 *  one) and optional for the rest.
 *
 *  Someone who may not clear holds (an operator) still can, with a supervisor who may
 *  signing in on their screen — as when another operator takes over a job (user ruling
 *  2026-11-16). Both are recorded: who cleared it, and who authorised it. */
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { holdReasonLabel, type WorkOrderHold } from "./WorkOrderHoldBanner";

export const NEEDS_RESOLUTION = new Set(["QUALITY", "TOOLING"]);

export type HoldSupervisor = { email: string; password: string };

export function ClearHoldDialog({ open, onOpenChange, hold, count, pending, onConfirm, needsSupervisor }: {
    open: boolean;
    onOpenChange: (o: boolean) => void;
    /** The hold being cleared; omit for a bulk clear of several. */
    hold?: WorkOrderHold | null;
    /** How many work orders a bulk clear covers. */
    count?: number;
    pending?: boolean;
    onConfirm: (notes: string, supervisor?: HoldSupervisor) => void;
    /** The person at the screen may not clear holds: a supervisor signs in to authorise it. */
    needsSupervisor?: boolean;
}) {
    const [notes, setNotes] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const required = !!hold && NEEDS_RESOLUTION.has(hold.reason);
    const signedIn = !needsSupervisor || (email.trim() !== "" && password !== "");
    const close = (o: boolean) => {
        onOpenChange(o);
        if (!o) { setNotes(""); setEmail(""); setPassword(""); }
    };
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
                        {needsSupervisor && " A supervisor must sign in below to authorise it — logged against their name."}
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-1.5">
                    <Label htmlFor="clear-hold-notes">
                        What resolved it{required ? " *" : " (optional)"}
                    </Label>
                    <Textarea id="clear-hold-notes" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)}
                              placeholder="e.g. Gauge recalibrated and verified; suspect parts re-inspected, all in spec." />
                </div>
                {needsSupervisor && (
                    <div className="space-y-2">
                        <p className="text-xs font-medium text-muted-foreground">Supervisor authorization</p>
                        <Input type="email" autoComplete="off" value={email}
                               onChange={(e) => setEmail(e.target.value)} placeholder="Supervisor email" />
                        <Input type="password" autoComplete="off" value={password}
                               onChange={(e) => setPassword(e.target.value)} placeholder="Supervisor password" />
                    </div>
                )}
                <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => close(false)}>Keep on hold</Button>
                    <Button type="button" disabled={pending || (required && !notes.trim()) || !signedIn}
                            onClick={() => onConfirm(notes.trim(),
                                needsSupervisor ? { email: email.trim(), password } : undefined)}>
                        {pending ? "Clearing…" : "Clear hold"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
