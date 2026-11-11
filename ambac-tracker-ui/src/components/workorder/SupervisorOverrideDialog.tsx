/**
 * The supervisor sign-in that clears a supervisor-overridable start refusal —
 * not qualified, assigned to someone else, the repeat-visit rule. Shared by every
 * start surface (Start Work, starting a load) so each offers the same escape.
 * A DIFFERENT supervisor re-authenticates; the server verifies them and logs the
 * override against their name.
 */
import { useState } from "react";
import { Loader2, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
    TrainingGateError,
    type OverrideCredentials,
    type TrainingGateInfo,
} from "@/hooks/useEnsureStepExecution";

export function SupervisorOverrideDialog({
    gate,
    onGateChange,
    onCancel,
    onAuthorize,
    submitLabel = "Authorize & start",
}: {
    gate: TrainingGateInfo | null;
    /** A retry refused again (bad password, not a supervisor…): the new reason. */
    onGateChange: (gate: TrainingGateInfo) => void;
    onCancel: () => void;
    /** Retry the start with the supervisor's credentials. Throws `TrainingGateError`
     *  when the retry is refused again. */
    onAuthorize: (override: OverrideCredentials) => Promise<void>;
    submitLabel?: string;
}) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [reason, setReason] = useState("");
    const [busy, setBusy] = useState(false);

    const reset = () => {
        setEmail("");
        setPassword("");
        setReason("");
    };
    const ready = email.trim() !== "" && password !== "" && reason.trim() !== "";

    const authorize = async () => {
        if (!ready) return;
        setBusy(true);
        try {
            await onAuthorize({ email: email.trim(), password, reason: reason.trim() });
            reset();
        } catch (e) {
            if (e instanceof TrainingGateError) {
                // Keep the panel open with the specific reason.
                onGateChange(e.gate);
                toast.error(e.gate.detail);
            } else {
                toast.error("Override failed", {
                    description: e instanceof Error ? e.message : undefined,
                });
            }
        } finally {
            setBusy(false);
        }
    };

    return (
        <Dialog
            open={!!gate}
            onOpenChange={(v) => {
                if (busy) return;
                if (!v) {
                    reset();
                    onCancel();
                }
            }}
        >
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <ShieldAlert className="h-5 w-5 text-destructive" />
                        {gate?.code === "assigned_to_other"
                            ? "Assigned to someone else"
                            : gate?.code === "revisit_rule"
                                ? "Repeat visit rule"
                                : "Not qualified for this step"}
                    </DialogTitle>
                    <DialogDescription>
                        {gate?.code === "assigned_to_other"
                            ? "This step is assigned to another operator. A supervisor must sign in below to reassign it — logged against their name."
                            : gate?.code === "revisit_rule"
                                ? `${gate.detail} A supervisor can sign in below to authorize it anyway — logged against their name.`
                                : "The operator isn't qualified. A supervisor must sign in below to authorize this work — logged against their name."}
                    </DialogDescription>
                </DialogHeader>

                {gate?.missing && gate.missing.length > 0 && (
                    <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3">
                        <p className="text-xs font-medium text-destructive mb-1.5">
                            Missing training
                        </p>
                        <ul className="space-y-1 text-sm">
                            {gate.missing.map((m, i) => (
                                <li key={i} className="flex justify-between gap-3">
                                    <span className="font-medium">{m.training}</span>
                                    <span className="text-xs text-muted-foreground">
                                        {m.reason}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {gate?.code === "assigned_to_other" && gate.assigned_to_name && (
                    <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3 text-sm">
                        Currently assigned to{" "}
                        <span className="font-medium">{gate.assigned_to_name}</span>.
                    </div>
                )}

                <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground">
                        Supervisor authorization
                    </p>
                    <Input
                        type="email"
                        autoComplete="off"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="Supervisor email"
                    />
                    <Input
                        type="password"
                        autoComplete="off"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Supervisor password"
                    />
                    <Textarea
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        placeholder={
                            gate?.code === "assigned_to_other"
                                ? "Reason for reassignment (required)"
                                : gate?.code === "revisit_rule"
                                    ? "Reason (required — e.g. nobody else on shift is trained)"
                                    : "Reason (required — e.g. line-down, trainee under direct supervision)"
                        }
                        rows={2}
                    />
                </div>

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => {
                            reset();
                            onCancel();
                        }}
                        disabled={busy}
                    >
                        Cancel
                    </Button>
                    <Button
                        variant="destructive"
                        onClick={authorize}
                        disabled={!ready || busy}
                    >
                        {busy ? (
                            <>
                                <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                                Authorizing…
                            </>
                        ) : (
                            submitLabel
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
