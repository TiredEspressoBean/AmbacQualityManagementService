/**
 * QA void affordance for a SubstepCompletion row.
 *
 * Triggered from the part traveler / step history when QA finds a
 * completion that's invalid after the fact (gauge out of cal, wrong
 * test method, calculator error). The void writes a `void_reason` on
 * the row; the advancement gate ignores voided rows from that point on,
 * so the next advancement attempt for the part will block on the
 * missing completion until a fresh one lands.
 *
 * For parts already past the step, voiding is audit-only — the
 * containment investigation lives in CAPA + the QualityReports list
 * page (Flow #10), not here.
 */

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

const csrfHeaders = () => ({ "X-CSRFToken": getCookie("csrftoken") ?? "" });

type VoidResponse = {
    id: string;
    is_voided: boolean;
    voided_at: string | null;
    void_reason: string;
};

function useVoidCompletion() {
    const qc = useQueryClient();
    return useMutation<VoidResponse, unknown, { id: string; reason: string }>({
        mutationFn: ({ id, reason }) =>
            api.api_SubstepCompletions_void_create(
                { reason } as never,
                { params: { id }, headers: csrfHeaders() },
                // Schema gap: void's response isn't declared on the endpoint,
                // so the generated type is the SubstepCompletion shape.
            ) as unknown as Promise<VoidResponse>,
        onSuccess: () => {
            // Refresh substep-completion + traveler queries so the
            // voided state reflects everywhere.
            qc.invalidateQueries({
                predicate: (q) =>
                    q.queryKey[0] === "substepCompletions" ||
                    q.queryKey[0] === "parts",
            });
        },
        meta: {
            errorMessage: "Couldn't void completion",
            successMessage: "Completion voided",
        },
    });
}

export function VoidCompletionDialog({
    completionId,
    completionTitle,
    open,
    onClose,
}: {
    completionId: string | null;
    completionTitle?: string;
    open: boolean;
    onClose: () => void;
}) {
    const [reason, setReason] = useState("");
    const voidMut = useVoidCompletion();

    const handleSubmit = () => {
        if (!completionId) return;
        const trimmed = reason.trim();
        if (!trimmed) {
            toast.error("A reason is required for an audit-defensible void.");
            return;
        }
        voidMut.mutate(
            { id: completionId, reason: trimmed },
            {
                onSuccess: () => {
                    setReason("");
                    onClose();
                },
            },
        );
    };

    return (
        <Dialog
            open={open}
            onOpenChange={(next) => {
                if (!next && !voidMut.isPending) {
                    setReason("");
                    onClose();
                }
            }}
        >
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Void substep completion</DialogTitle>
                </DialogHeader>
                <div className="space-y-3">
                    <p className="text-sm text-muted-foreground">
                        {completionTitle ? (
                            <>Voiding completion for <span className="font-medium">{completionTitle}</span>.</>
                        ) : (
                            <>Voiding this completion.</>
                        )}{" "}
                        The advancement gate will block any part downstream that depends
                        on this completion until a fresh one lands.
                    </p>
                    <div className="space-y-1">
                        <Label htmlFor="void-reason" className="text-xs">
                            Reason (required)
                        </Label>
                        <Textarea
                            id="void-reason"
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="e.g., Gauge XYZ found out of calibration on Tuesday — voiding all torque captures since Monday."
                            rows={4}
                            autoFocus
                        />
                    </div>
                </div>
                <DialogFooter>
                    <Button
                        variant="ghost"
                        onClick={onClose}
                        disabled={voidMut.isPending}
                    >
                        Cancel
                    </Button>
                    <Button
                        variant="destructive"
                        onClick={handleSubmit}
                        disabled={voidMut.isPending || !reason.trim()}
                    >
                        {voidMut.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Void completion
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
