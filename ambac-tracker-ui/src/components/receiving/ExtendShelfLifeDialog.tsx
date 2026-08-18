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
import { Textarea } from "@/components/ui/textarea";
import { useExtendShelfLife } from "@/hooks/useReceivingMutations";

type Props = {
    lotId: string;
    lotNumber: string;
    /** Current use-by, prefilled as the starting point (ISO yyyy-mm-dd) or null. */
    currentExpiration?: string | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
};

/**
 * Governed shelf-life extension: a re-tested lot gets a new use-by date with a
 * required justification. The approver is the request user (server-side). If the
 * lot was quarantined solely for shelf life, the backend re-qualifies it.
 */
export function ExtendShelfLifeDialog({ lotId, lotNumber, currentExpiration, open, onOpenChange }: Props) {
    const [newDate, setNewDate] = useState("");
    const [reason, setReason] = useState("");
    const extend = useExtendShelfLife();

    const reset = () => {
        setNewDate("");
        setReason("");
    };

    const canSubmit = newDate !== "" && reason.trim() !== "" && !extend.isPending;

    const submit = () => {
        if (!canSubmit) return;
        extend.mutate(
            { id: lotId, new_expiration_date: newDate, reason: reason.trim() },
            {
                onSuccess: () => {
                    toast.success(`Shelf life extended for lot ${lotNumber}`);
                    reset();
                    onOpenChange(false);
                },
                onError: (err: unknown) => {
                    const detail =
                        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
                    toast.error(detail ?? "Could not extend shelf life");
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
                    <DialogTitle>Extend shelf life · Lot {lotNumber}</DialogTitle>
                    <DialogDescription>
                        Record a new use-by date after re-test/re-certification. A justification is
                        required and captured on the audit trail.
                        {currentExpiration ? ` Current use-by: ${currentExpiration}.` : ""}
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-2">
                    <div className="space-y-1.5">
                        <Label htmlFor="esl-date">New use-by date</Label>
                        <Input
                            id="esl-date"
                            type="date"
                            value={newDate}
                            onChange={(e) => setNewDate(e.target.value)}
                        />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="esl-reason">Justification</Label>
                        <Textarea
                            id="esl-reason"
                            placeholder="e.g. Re-tested viscosity within spec; CoA #… attached."
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            rows={3}
                        />
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={extend.isPending}>
                        Cancel
                    </Button>
                    <Button onClick={submit} disabled={!canSubmit}>
                        {extend.isPending ? "Extending…" : "Extend shelf life"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
