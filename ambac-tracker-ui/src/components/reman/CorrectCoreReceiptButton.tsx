import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CoreOrderSelect, ORDER_NONE } from "@/components/reman/CoreOrderSelect";
import { api } from "@/lib/api/generated";
import { apiErrorMessage } from "@/lib/api/describeApiError";

type Mode = "EXCHANGE" | "REPAIR_RETURN";

/**
 * A core's order or its exchange / repair-and-return mode was recorded wrong at receipt:
 * correct it, with a reason, while it is still Received — before teardown, when harvest,
 * reservations and authorisation start to follow from it (Corrections #21).
 */
export function CorrectCoreReceiptButton({ core }: {
    core: { id: string; core_number?: string; customer?: string | number | null;
            fulfilment_mode?: string | null; order?: string | null };
}) {
    const queryClient = useQueryClient();
    const [open, setOpen] = useState(false);
    const [mode, setMode] = useState<Mode>((core.fulfilment_mode as Mode) ?? "EXCHANGE");
    const [order, setOrder] = useState<string>(core.order ?? ORDER_NONE);
    const [reason, setReason] = useState("");
    const mut = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: () => api.api_Cores_correct_receipt_create(
            { fulfilment_mode: mode, order: order === ORDER_NONE ? null : order, reason: reason.trim() },
            { params: { id: String(core.id) } }),
        onSuccess: () => {
            queryClient.invalidateQueries();
            toast.success(`${core.core_number ?? "Core"} — receipt corrected`);
            setOpen(false);
            setReason("");
        },
        onError: (e: unknown) => toast.error(apiErrorMessage(e) ?? "Couldn't correct the receipt"),
    });
    const changed = mode !== core.fulfilment_mode || (order === ORDER_NONE ? null : order) !== (core.order ?? null);
    return (
        <>
            <Button variant="ghost" onClick={() => setOpen(true)}>Correct receipt…</Button>
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Correct the receipt · {core.core_number}</DialogTitle>
                        <DialogDescription>
                            The order or the mode was recorded wrong. They can be corrected while the core is
                            Received — before teardown. Each change and your reason are kept on the core.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3">
                        <div className="space-y-1.5">
                            <Label>Mode</Label>
                            <Select value={mode} onValueChange={(v) => setMode(v as Mode)}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="EXCHANGE">Exchange — the unit becomes our stock</SelectItem>
                                    <SelectItem value="REPAIR_RETURN">Repair and return — the customer&rsquo;s own unit</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5">
                            <Label>For order{mode === "REPAIR_RETURN" ? " *" : ""}</Label>
                            <CoreOrderSelect companyId={core.customer ? String(core.customer) : null}
                                value={order} onChange={setOrder} required={mode === "REPAIR_RETURN"} />
                        </div>
                        <Textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} aria-label="Reason"
                            placeholder="Why — e.g. received as exchange; the customer's paperwork says repair and return" />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpen(false)} disabled={mut.isPending}>Cancel</Button>
                        <Button onClick={() => mut.mutate()} disabled={!changed || !reason.trim() || mut.isPending}>
                            {mut.isPending ? "Saving…" : "Correct"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
