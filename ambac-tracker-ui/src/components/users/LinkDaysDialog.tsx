/**
 * How long a link works, asked before it's made — the same for an invitation and a
 * reset link (one behaviour to learn; user ruling 2026-11-19). 1 to 30 days, 7 unless
 * changed (services/core/sign_in.LINK_DAYS_DEFAULT).
 */
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const LINK_DAYS_DEFAULT = 7;
export const LINK_DAYS_MAX = 30;

/** What the link dialog says once a link is made — the same words for both kinds. */
export const linkValidUntil = (name: string, expiresAt: string | Date, pending = false) => {
    const until = new Date(expiresAt).toLocaleString();
    return pending
        ? `Already invited — this link works until ${until}.`
        : `Give this link to ${name} in person. It works once, until ${until}.`;
};

export function LinkDaysDialog({ open, onOpenChange, title, name, actionLabel, onCreate }: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    title: string;
    name: string;
    actionLabel: string;
    onCreate: (days: number) => Promise<unknown>;
}) {
    const [days, setDays] = useState(String(LINK_DAYS_DEFAULT));
    const [pending, setPending] = useState(false);
    useEffect(() => { if (open) setDays(String(LINK_DAYS_DEFAULT)); }, [open]);
    const n = Number(days);
    const valid = Number.isInteger(n) && n >= 1 && n <= LINK_DAYS_MAX;

    const create = async () => {
        if (!valid) return;
        setPending(true);
        try {
            await onCreate(n);
            onOpenChange(false);
        } finally {
            setPending(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-sm">
                <DialogHeader>
                    <DialogTitle>{title}</DialogTitle>
                    <DialogDescription>
                        A link for {name} to hand over in person. It works once.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-2">
                    <Label htmlFor="link-days">Valid for (days)</Label>
                    <Input id="link-days" type="number" min={1} max={LINK_DAYS_MAX} className="w-28"
                           value={days} onChange={(e) => setDays(e.target.value)} />
                    {!valid && (
                        <p className="text-xs text-destructive">1 to {LINK_DAYS_MAX} days.</p>
                    )}
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
                    <Button disabled={!valid || pending} onClick={create}>
                        {pending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {actionLabel}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
