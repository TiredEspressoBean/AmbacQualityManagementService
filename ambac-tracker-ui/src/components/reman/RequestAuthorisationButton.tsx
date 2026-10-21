/** Send a repair-and-return unit for its customer's authorisation — confirmed first,
 *  naming the repairs being asked about and the finding behind each, as the
 *  Approved… / Declined… dialogs show what was agreed to. */
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { useRetrieveCore } from "@/hooks/useRetrieveCore";
import { useCoreLifecycleAction } from "@/hooks/useReleaseCore";
import { apiErrorMessage } from "@/lib/api/describeApiError";

export function RequestAuthorisationButton({ coreId, coreNumber, size = "sm", variant = "ghost" }: {
    coreId: string;
    coreNumber?: string;
    size?: "sm" | "default";
    variant?: "ghost" | "outline";
}) {
    const [open, setOpen] = useState(false);
    const lifecycle = useCoreLifecycleAction();
    const { data: core } = useRetrieveCore(open ? coreId : "");
    const scope = core?.authorisation_needed ?? [];
    const send = () =>
        lifecycle.mutate({ id: coreId, action: "request_authorisation" }, {
            onSuccess: () => { toast.success(`${coreNumber ?? "Core"} — sent for customer authorisation`); setOpen(false); },
            onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't send for authorisation"),
        });
    return (
        <>
            <Button type="button" size={size} variant={variant} onClick={() => setOpen(true)}>
                Authorise…
            </Button>
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Send {coreNumber ?? "this unit"} for the customer's authorisation?</DialogTitle>
                        <DialogDescription>
                            The unit waits for their answer before this work goes ahead. Record what
                            they say with Approved… or Declined….
                        </DialogDescription>
                    </DialogHeader>
                    {scope.length === 0 ? (
                        <p className="text-sm text-muted-foreground">
                            {core ? "Nothing on this unit needs their approval." : "Loading what they'd be asked about…"}
                        </p>
                    ) : (
                        <ul className="space-y-2 text-sm">
                            {scope.map((s) => (
                                <li key={s.code}>
                                    <span className="font-medium">{s.code}</span>
                                    {s.name ? <span className="text-muted-foreground"> — {s.name}</span> : null}
                                    {s.why.length > 0 && (
                                        <div className="text-xs text-muted-foreground">{s.why.join("; ")}</div>
                                    )}
                                </li>
                            ))}
                        </ul>
                    )}
                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                        <Button type="button" disabled={lifecycle.isPending || scope.length === 0} onClick={send}>
                            {lifecycle.isPending ? "Sending…" : "Send for authorisation"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
