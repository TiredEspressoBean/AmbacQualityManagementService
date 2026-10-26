import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/generated";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { usePermissionSet } from "@/hooks/useMyPermissions";

/**
 * A training override that shouldn't have been given: flag it for QA review, with a
 * reason. The override stays — the work happened under it — and the flag shows in the
 * QA manager's overrides review. For the override authority (leads, QA, production).
 */
export function FlagOverrideButton({ executionId, flagged }: { executionId: string; flagged: boolean }) {
    const { has } = usePermissionSet();
    const queryClient = useQueryClient();
    const [open, setOpen] = useState(false);
    const [reason, setReason] = useState("");
    const mut = useMutation({
        mutationFn: () => api.api_StepExecutions_flag_override_create(
            { reason: reason.trim() }, { params: { id: executionId } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) =>
                q.queryKey[0] === "training-overrides" || (q.queryKey[0] === "parts" && q.queryKey[1] === "traveler") });
            toast.success("Override flagged for QA review.");
            setOpen(false);
            setReason("");
        },
        onError: (e: unknown) => toast.error(apiErrorMessage(e) ?? "Could not flag the override"),
    });

    if (flagged || !has("override_training_gate")) return null;
    return (
        <>
            <button type="button" className="ml-2 underline hover:text-foreground" onClick={() => setOpen(true)}>
                Flag for QA review
            </button>
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Flag this override for QA review</DialogTitle>
                        <DialogDescription>
                            The override stays on record — the work was done under it. The flag and your
                            reason show in the training overrides review for QA to look into.
                        </DialogDescription>
                    </DialogHeader>
                    <Textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} aria-label="Reason"
                        placeholder="Why — e.g. the operator's certificate had lapsed; I shouldn't have authorised it" />
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpen(false)} disabled={mut.isPending}>Cancel</Button>
                        <Button onClick={() => mut.mutate()} disabled={!reason.trim() || mut.isPending}>
                            {mut.isPending ? "Flagging…" : "Flag for review"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
