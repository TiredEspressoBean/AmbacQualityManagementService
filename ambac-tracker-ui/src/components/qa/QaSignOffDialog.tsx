import { useEffect, useState, useRef } from "react";
import { toast } from "sonner";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
    AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSignOffStep } from "@/hooks/useInspectionInbox";
import { apiErrorMessage } from "@/lib/api/describeApiError";

export type SignOffTarget = {
    workOrderId: string;
    stepId: string;
    step: string;
    workOrder: string;
    units: number;
    /** The step's authored assurance: "PASSWORD" asks the signer to re-enter their
     *  own password, anything else records the sign-off under their login. */
    assurance?: string;
};

/**
 * Sign off a QA-gated step for a work order — the step-level "QA sign-off required"
 * gate. The signer vouches the step's work is acceptable; the units then move on.
 * Whoever did the step's work can't sign it (the server refuses, and says why).
 *
 * How much is asked of the signer is the process author's choice, not this dialog's:
 * a step authored as *signature + password* asks for their own password here, and the
 * server verifies it against the step rather than trusting what the client sends. A
 * password typed into a step that didn't ask for one is ignored, not honoured.
 */
export function QaSignOffDialog({ target, onOpenChange }: {
    target: SignOffTarget | null;
    onOpenChange: (open: boolean) => void;
}) {
    const signOff = useSignOffStep();
    const [password, setPassword] = useState("");
    // Render from the last target while the dialog animates closed: the caller clears
    // `target` to close it, and the closing frames read "Sign off ?" with every field
    // blank, which looked like a dialog left open after a successful sign-off.
    const last = useRef<SignOffTarget | null>(target);
    if (target) last.current = target;
    const shown = target ?? last.current;
    const needsPassword = target?.assurance === "PASSWORD";

    // Never carry a typed password from one sign-off to the next.
    useEffect(() => { setPassword(""); }, [target?.stepId, target?.workOrderId]);

    const submit = () => {
        if (!target) return;
        signOff.mutate(
            {
                work_order: target.workOrderId,
                step: target.stepId,
                ...(needsPassword ? { password } : {}),
            },
            {
                onSuccess: (r) => {
                    toast.success(`${target.step} signed off`, {
                        description: r.parts_advanced
                            ? `${r.parts_advanced} unit${r.parts_advanced === 1 ? "" : "s"} moved on.`
                            : "The lot moves on when its other units finish this step.",
                    });
                    setPassword("");
                    onOpenChange(false);
                },
                // The password stays typed on a refusal — a wrong one is usually a
                // typo, and clearing the field makes the retry worse.
                onError: (err) => toast.error("Couldn't sign off", {
                    description: apiErrorMessage(err) ?? "The sign-off was refused.",
                }),
            },
        );
    };

    return (
        <AlertDialog open={target !== null} onOpenChange={onOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Sign off {shown?.step}?</AlertDialogTitle>
                    <AlertDialogDescription>
                        {shown?.units} unit{shown?.units === 1 ? "" : "s"} on <span className="font-mono">{shown?.workOrder}</span>{" "}
                        {shown?.units === 1 ? "is" : "are"} waiting at {shown?.step} for a QA sign-off. Signing records you
                        as having accepted the step&rsquo;s work. The lot moves on to its next step once
                        every unit in it is ready — if others haven&rsquo;t finished this step, it waits for them.
                        {needsPassword
                            ? " This step is authored to need your password as well, so the record says it was you and nobody else."
                            : null}
                    </AlertDialogDescription>
                </AlertDialogHeader>
                {needsPassword && (
                    <div className="space-y-1.5">
                        <Label htmlFor="qa-signoff-password">Your password</Label>
                        <Input
                            id="qa-signoff-password"
                            type="password"
                            autoComplete="current-password"
                            value={password}
                            disabled={signOff.isPending}
                            onChange={(e) => setPassword(e.target.value)}
                            onKeyDown={(e) => { if (e.key === "Enter" && password) submit(); }}
                        />
                    </div>
                )}
                <AlertDialogFooter>
                    <AlertDialogCancel disabled={signOff.isPending}>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                        disabled={signOff.isPending || !target || (needsPassword && !password)}
                        onClick={(e) => { e.preventDefault(); submit(); }}
                    >
                        {signOff.isPending ? "Signing…" : "Sign off"}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
