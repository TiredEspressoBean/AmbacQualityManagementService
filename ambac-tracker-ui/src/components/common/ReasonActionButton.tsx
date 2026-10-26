import { useState, type ReactNode } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { apiErrorMessage } from "@/lib/api/describeApiError";

type Props = {
    /** The button's label, and the confirm button's unless `confirmLabel` is given. */
    label: string;
    title: string;
    /** What happens, in the user's terms, and that the reason is kept. */
    description: ReactNode;
    placeholder?: string;
    confirmLabel?: string;
    /** Shown on success — or worked out from the response, when what happened varies. */
    done: string | ((result: unknown) => string);
    /** Performs the correction with the reason the user gave. */
    run: (reason: string) => Promise<unknown>;
    variant?: "outline" | "ghost" | "default" | "destructive";
    size?: "sm" | "default";
    destructive?: boolean;
};

/**
 * A correction that needs a reason: a button, a dialog asking why, and the call. The
 * shape every "put a mistake right" action shares — the reason is required and kept on
 * the record server-side. Everything is refreshed afterwards, since a correction can
 * touch several records.
 */
export function ReasonActionButton({
    label, title, description, placeholder, confirmLabel, done, run,
    variant = "outline", size = "sm", destructive = false,
}: Props) {
    const queryClient = useQueryClient();
    const [open, setOpen] = useState(false);
    const [reason, setReason] = useState("");
    const mut = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: () => run(reason.trim()),
        onSuccess: (result) => {
            queryClient.invalidateQueries();
            toast.success(typeof done === "function" ? done(result) : done);
            setOpen(false);
            setReason("");
        },
        onError: (e: unknown) => toast.error(apiErrorMessage(e) ?? `Couldn't ${label.toLowerCase()}`),
    });
    return (
        <>
            <Button size={size} variant={variant} onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpen(true); }}>
                {label}
            </Button>
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent onClick={(e) => e.stopPropagation()}>
                    <DialogHeader>
                        <DialogTitle>{title}</DialogTitle>
                        <DialogDescription asChild><div>{description}</div></DialogDescription>
                    </DialogHeader>
                    <Textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)}
                        placeholder={placeholder ?? "Why"} aria-label="Reason" />
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpen(false)} disabled={mut.isPending}>Cancel</Button>
                        <Button variant={destructive ? "destructive" : "default"}
                            onClick={() => mut.mutate()} disabled={!reason.trim() || mut.isPending}>
                            {mut.isPending ? "Saving…" : confirmLabel ?? label}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
