import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Send, CheckSquare } from "lucide-react";
import { toast } from "sonner";
import { ReasonPromptDialog } from "./ReasonPromptDialog";
import { useReleasePcn, useClosePcn } from "@/hooks/useChangeControlActions";
import { usePermissionSet } from "@/hooks/useMyPermissions";

type Props = { pcnId: string; status: string };

export function PcnActions({ pcnId, status }: Props) {
    const [closeOpen, setCloseOpen] = useState(false);
    const release = useReleasePcn();
    const close = useClosePcn();
    const { has } = usePermissionSet();

    const canChange = has("change_processchangenotice");
    const canRelease = canChange && status === "DRAFT";
    const canClose = canChange && (status === "RELEASED" || status === "ACKNOWLEDGED");

    if (!canRelease && !canClose) return null;

    return (
        <div className="flex gap-2">
            {canRelease && (
                <Button
                    size="sm"
                    onClick={async () => {
                        try {
                            await release.mutateAsync({ id: pcnId });
                            toast.success("PCN released");
                        } catch (e) {
                            toast.error("Release failed", { description: e instanceof Error ? e.message : undefined });
                        }
                    }}
                    disabled={release.isPending}
                >
                    <Send className="h-4 w-4 mr-2" />
                    {release.isPending ? "…" : "Release"}
                </Button>
            )}
            {canClose && (
                <Button size="sm" onClick={() => setCloseOpen(true)}>
                    <CheckSquare className="h-4 w-4 mr-2" /> Close
                </Button>
            )}

            <ReasonPromptDialog
                open={closeOpen}
                onOpenChange={setCloseOpen}
                title="Close PCN"
                description="Record closure evidence (training completed, audits passed, etc.)."
                label="Closure evidence"
                placeholder="e.g. Operator training complete on 2026-06-15; AS9100 audit passed."
                confirmLabel="Close PCN"
                pending={close.isPending}
                onSubmit={async (evidence) => {
                    try {
                        await close.mutateAsync({ id: pcnId, closure_evidence: evidence });
                        toast.success("PCN closed");
                        setCloseOpen(false);
                    } catch (e) {
                        toast.error("Close failed", { description: e instanceof Error ? e.message : undefined });
                    }
                }}
            />
        </div>
    );
}
