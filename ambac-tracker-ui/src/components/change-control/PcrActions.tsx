import { useState } from "react";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Ban } from "lucide-react";
import { toast } from "sonner";
import { ReasonPromptDialog } from "./ReasonPromptDialog";
import { PcrConflictDialog } from "./PcrConflictDialog";
import {
    useApprovePcr, useRejectPcr, useCancelPcr,
    PcrRebaseConflictError, type RebaseConflict,
} from "@/hooks/useChangeControlActions";
import { usePermissionSet } from "@/hooks/useMyPermissions";

type Props = { pcrId: string; status: string };

export function PcrActions({ pcrId, status }: Props) {
    const [rejectOpen, setRejectOpen] = useState(false);
    const [cancelOpen, setCancelOpen] = useState(false);
    const [conflict, setConflict] = useState<RebaseConflict | null>(null);

    const approve = useApprovePcr();
    const reject = useRejectPcr();
    const cancel = useCancelPcr();
    const { has } = usePermissionSet();

    // All PCR lifecycle transitions are state changes on the PCR row, so
    // `change_processchangerequest` is the canonical gate — matches
    // `action_permissions` on the viewset.
    const canChange = has("change_processchangerequest");
    const isApprovable = canChange && (status === "SUBMITTED" || status === "UNDER_REVIEW");
    const isCancellable = canChange && (status === "DRAFT" || status === "SUBMITTED" || status === "UNDER_REVIEW");

    if (!isApprovable && !isCancellable) return null;

    return (
        <div className="flex gap-2">
            {isApprovable && (
                <>
                    <Button
                        size="sm"
                        onClick={async () => {
                            try {
                                const result = await approve.mutateAsync({ id: pcrId });
                                if (result?.rebase?.rebased) {
                                    toast.success("PCR approved", {
                                        description: "Your draft was re-anchored onto the newer approved baseline before approval — non-conflicting changes were lifted forward.",
                                    });
                                } else {
                                    toast.success("PCR approved");
                                }
                            } catch (e) {
                                if (e instanceof PcrRebaseConflictError) {
                                    setConflict(e.conflict);
                                    return;
                                }
                                toast.error("Approve failed", { description: e instanceof Error ? e.message : undefined });
                            }
                        }}
                        disabled={approve.isPending}
                    >
                        <CheckCircle2 className="h-4 w-4 mr-2" />
                        {approve.isPending ? "Approving…" : "Approve"}
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => setRejectOpen(true)}>
                        <XCircle className="h-4 w-4 mr-2" />
                        Reject
                    </Button>
                </>
            )}
            {isCancellable && (
                <Button size="sm" variant="outline" onClick={() => setCancelOpen(true)}>
                    <Ban className="h-4 w-4 mr-2" />
                    Cancel
                </Button>
            )}

            <ReasonPromptDialog
                open={rejectOpen}
                onOpenChange={setRejectOpen}
                title="Reject PCR"
                description="Provide a reason — this will be visible to the submitter."
                placeholder="Why is this change being rejected?"
                confirmLabel="Reject"
                confirmVariant="destructive"
                pending={reject.isPending}
                onSubmit={async (reason) => {
                    try {
                        await reject.mutateAsync({ id: pcrId, reason });
                        toast.success("PCR rejected");
                        setRejectOpen(false);
                    } catch (e) {
                        toast.error("Reject failed", { description: e instanceof Error ? e.message : undefined });
                    }
                }}
            />
            <ReasonPromptDialog
                open={cancelOpen}
                onOpenChange={setCancelOpen}
                title="Cancel PCR"
                description="The PCR will be marked CANCELLED. Optional: leave a note for the audit log."
                placeholder="Optional reason"
                confirmLabel="Cancel PCR"
                required={false}
                pending={cancel.isPending}
                onSubmit={async (reason) => {
                    try {
                        await cancel.mutateAsync({ id: pcrId, reason });
                        toast.success("PCR cancelled");
                        setCancelOpen(false);
                    } catch (e) {
                        toast.error("Cancel failed", { description: e instanceof Error ? e.message : undefined });
                    }
                }}
            />
            <PcrConflictDialog
                open={conflict !== null}
                onOpenChange={(open) => { if (!open) setConflict(null); }}
                conflict={conflict}
            />
        </div>
    );
}
