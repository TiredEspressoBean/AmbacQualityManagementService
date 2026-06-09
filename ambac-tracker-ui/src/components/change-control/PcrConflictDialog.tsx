import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";
import type { RebaseConflict } from "@/hooks/useChangeControlActions";

type Props = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    conflict: RebaseConflict | null;
};

/**
 * Rendered when a PCR approval is rejected because the draft conflicts
 * with intervening approved changes. Lists each (step, field) pair
 * where the engineer's intent collides with the new baseline value.
 *
 * Resolution is manual: engineer cancels this PCR or edits the draft
 * to match the new baseline before re-submitting. The system doesn't
 * silently squash overlaps — regulated change control requires
 * deliberate human resolution per IATF 16949 / AS9100 8.5.6.
 */
export function PcrConflictDialog({ open, onOpenChange, conflict }: Props) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-2xl">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-amber-600" />
                        Conflicts with newer approved changes
                    </DialogTitle>
                    <DialogDescription>
                        Another PCR was approved against this process while this draft was
                        open. The fields below were modified on both — resolve manually
                        before approval can proceed.
                    </DialogDescription>
                </DialogHeader>

                {conflict && (
                    <div className="space-y-2 py-2">
                        {conflict.conflicts.map((c, i) => (
                            <div key={i} className="rounded-md border p-3 text-sm">
                                <div className="font-medium">{c.step_name || "(unnamed step)"}</div>
                                <div className="text-xs text-muted-foreground mt-1">
                                    Field: <span className="font-mono">{c.field}</span>
                                </div>
                                <div className="grid grid-cols-2 gap-3 mt-2 text-sm">
                                    <div>
                                        <div className="text-xs text-muted-foreground">Your draft wants</div>
                                        <div className="font-mono">{formatValue(c.intent_value)}</div>
                                    </div>
                                    <div>
                                        <div className="text-xs text-muted-foreground">Current approved</div>
                                        <div className="font-mono">{formatValue(c.approved_value)}</div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                <DialogFooter>
                    <Button onClick={() => onOpenChange(false)}>Close</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function formatValue(v: unknown): string {
    if (v === null || v === undefined) return "—";
    if (typeof v === "boolean") return v ? "true" : "false";
    return String(v);
}
