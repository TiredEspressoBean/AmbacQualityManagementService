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

type Kind = "request" | "response";

const COPY: Record<Kind, { button: string; title: string; body: string; placeholder: string; done: string }> = {
    request: {
        button: "Withdraw request",
        title: "Withdraw this approval request",
        body: "The approvers are no longer asked to decide. A document goes back to draft so you can change it and submit again. Your reason is kept on the request's record.",
        placeholder: "Why — e.g. wrong classification; correcting it before review",
        done: "Request withdrawn — you can edit and submit again.",
    },
    response: {
        button: "Change my response",
        title: "Withdraw your response",
        body: "Your answer is taken back while the request is still open, and you're asked again — answer anew when ready. The answer you gave and your reason stay on record.",
        placeholder: "Why — e.g. approved the wrong revision",
        done: "Response withdrawn — you can respond again.",
    },
};

function WithdrawButton({ kind, approvalId, onDone, size = "sm" }: {
    kind: Kind; approvalId: string; onDone?: () => void; size?: "sm" | "default";
}) {
    const queryClient = useQueryClient();
    const [open, setOpen] = useState(false);
    const [reason, setReason] = useState("");
    const copy = COPY[kind];
    const mut = useMutation({
        mutationFn: (): Promise<unknown> => kind === "request"
            ? api.api_ApprovalRequests_withdraw_create({ reason: reason.trim() }, { params: { id: approvalId } })
            : api.api_ApprovalRequests_withdraw_response_create({ reason: reason.trim() }, { params: { id: approvalId } }),
        onSuccess: () => {
            // Approvals and the document they gate.
            queryClient.invalidateQueries();
            toast.success(copy.done);
            setOpen(false);
            setReason("");
            onDone?.();
        },
        onError: (e: unknown) => toast.error(apiErrorMessage(e) ?? "Couldn't withdraw it"),
    });
    return (
        <>
            <Button size={size} variant="outline" onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpen(true); }}>
                {copy.button}
            </Button>
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent onClick={(e) => e.stopPropagation()}>
                    <DialogHeader>
                        <DialogTitle>{copy.title}</DialogTitle>
                        <DialogDescription>{copy.body}</DialogDescription>
                    </DialogHeader>
                    <Textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)}
                        placeholder={copy.placeholder} aria-label="Reason" />
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpen(false)} disabled={mut.isPending}>Cancel</Button>
                        <Button onClick={() => mut.mutate()} disabled={!reason.trim() || mut.isPending}>
                            {mut.isPending ? "Withdrawing…" : copy.button}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}

/** The requester takes back a request still waiting on its approvers. */
export function WithdrawRequestButton(props: { approvalId: string; onDone?: () => void; size?: "sm" | "default" }) {
    return <WithdrawButton kind="request" {...props} />;
}

/** An approver takes back their own answer while the request is still open. */
export function WithdrawResponseButton(props: { approvalId: string; onDone?: () => void; size?: "sm" | "default" }) {
    return <WithdrawButton kind="response" {...props} />;
}
