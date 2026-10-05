/** Scrap a core, and record that its core credit was issued — core detail's actions.
 *
 * Both were inert: "Scrap" navigated to a /reman/cores/$id/scrap route that never
 * existed (and was offered only at RECEIVED), and "Issue Credit" had no handler.
 */
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { DollarSign, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { useScrapCore } from "@/hooks/useScrapCore";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import { isScrappable } from "@/lib/reman/core-stages";

function detailOf(err: unknown, fallback: string) {
    const d = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    return d ?? fallback;
}

export function ScrapCoreButton({ core }: {
    core: { id: string | number; core_number?: string; status?: string; fulfilment_mode?: string };
}) {
    const [open, setOpen] = useState(false);
    const [reason, setReason] = useState("");
    const scrap = useScrapCore();
    if (!isScrappable(core.status)) return null;
    const theirs = core.fulfilment_mode === "REPAIR_RETURN";

    const submit = () =>
        scrap.mutate(
            { id: String(core.id), reason: reason.trim() },
            {
                onSuccess: () => { toast.success(`${core.core_number ?? "Core"} scrapped`); setOpen(false); setReason(""); },
                onError: (e) => toast.error(detailOf(e, "Could not scrap the core.")),
            },
        );

    return (
        <>
            <Button variant="destructive" onClick={() => setOpen(true)}>
                <Trash2 className="mr-2 h-4 w-4" /> Scrap
            </Button>
            <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) setReason(""); }}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Scrap {core.core_number}</DialogTitle>
                        <DialogDescription>
                            The unit is beyond use. This ends it — its part is scrapped with it, and
                            its work order closes if nothing else on it is open.
                            {theirs && " It is the customer's unit (repair-and-return), so the reason is what they will be told."}
                        </DialogDescription>
                    </DialogHeader>
                    <Textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)}
                              placeholder="e.g. Cracked body found at teardown, beyond repair limits" />
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                        <Button variant="destructive" disabled={!reason.trim() || scrap.isPending} onClick={submit}>
                            {scrap.isPending ? "Scrapping…" : "Scrap core"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}

/** Records that the core credit was issued. Informational: the credit itself is
 *  settled in the accounting system — UQMES only keeps that it happened. */
export function IssueCreditButton({ core }: {
    core: { id: string | number; core_credit_issued?: boolean; core_credit_value?: string | null };
}) {
    const qc = useQueryClient();
    const issue = useMutation({
        mutationFn: () =>
            api.api_Cores_issue_credit_create(undefined, {
                params: { id: String(core.id) },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            toast.success("Core credit recorded as issued");
            qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "cores" || q.queryKey[0] === "core" });
        },
        onError: (e) => toast.error(detailOf(e, "Could not record the credit.")),
    });
    if (core.core_credit_issued || !core.core_credit_value) return null;
    return (
        <Button variant="outline" disabled={issue.isPending} onClick={() => issue.mutate()}>
            <DollarSign className="mr-2 h-4 w-4" /> Issue Credit
        </Button>
    );
}
