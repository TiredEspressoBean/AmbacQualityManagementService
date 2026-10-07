import { toast } from "sonner";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
    AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useSignOffStep } from "@/hooks/useInspectionInbox";
import { apiErrorMessage } from "@/lib/api/describeApiError";

export type SignOffTarget = { workOrderId: string; stepId: string; step: string; workOrder: string; units: number };

/**
 * Sign off a QA-gated step for a work order — the step-level "QA sign-off required"
 * gate. The signer vouches the step's work is acceptable; the units then move on.
 * Whoever did the step's work can't sign it (the server refuses, and says why).
 */
export function QaSignOffDialog({ target, onOpenChange }: {
    target: SignOffTarget | null;
    onOpenChange: (open: boolean) => void;
}) {
    const signOff = useSignOffStep();
    return (
        <AlertDialog open={target !== null} onOpenChange={onOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Sign off {target?.step}?</AlertDialogTitle>
                    <AlertDialogDescription>
                        {target?.units} unit{target?.units === 1 ? "" : "s"} on <span className="font-mono">{target?.workOrder}</span>{" "}
                        {target?.units === 1 ? "is" : "are"} waiting at {target?.step} for a QA sign-off. Signing records you
                        as having accepted the step&rsquo;s work. The lot moves on to its next step once
                        every unit in it is ready — if others haven&rsquo;t finished this step, it waits for them.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel disabled={signOff.isPending}>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                        disabled={signOff.isPending || !target}
                        onClick={(e) => {
                            e.preventDefault();
                            if (!target) return;
                            signOff.mutate({ work_order: target.workOrderId, step: target.stepId }, {
                                onSuccess: (r) => {
                                    toast.success(`${target.step} signed off`, {
                                        description: r.parts_advanced
                                            ? `${r.parts_advanced} unit${r.parts_advanced === 1 ? "" : "s"} moved on.`
                                            : "The lot moves on when its other units finish this step.",
                                    });
                                    onOpenChange(false);
                                },
                                onError: (err) => toast.error("Couldn't sign off", {
                                    description: apiErrorMessage(err) ?? "The sign-off was refused.",
                                }),
                            });
                        }}
                    >
                        {signOff.isPending ? "Signing…" : "Sign off"}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
