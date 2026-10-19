/** The FPI buy-off attestation dialog, in both of its modes.
 *
 *  Mode depends on who is at the keyboard:
 *
 *  - **QA's own session** (`canSignOff`) — notes only, plus their own password
 *    when the step's author set its QA assurance to signature + password. The
 *    buy-off IS this step's QA release, so it meets the bar the author set; a
 *    gate you can walk around by releasing through FPI is not a gate. Used from
 *    the banner and from the pending-FPI panel on WO Control.
 *  - **The operator's station** (`!canSignOff`) — additionally collects a QA
 *    email plus signature/password, verified inline server-side. The QA person
 *    is never logged in on that terminal, and the verdict is attributed to
 *    them, not to the operator. This is the standard second-person buy-off for
 *    a shop-floor hold point.
 *
 *  Shared rather than inlined because three surfaces need it: the review
 *  stage's FPI hold, the WO Control panel, and the runtime banner.
 */
import { useCallback, useState } from "react";
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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    SignatureVerification,
    validateSignatureVerification,
    type SignatureVerificationData,
} from "@/components/approval/SignatureVerification";
import { useFpiPass } from "@/hooks/useFpiRecords";
import { apiErrorMessage } from "@/lib/api/describeApiError";

type FpiSignOffDialogProps = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    /** The PENDING FPIRecord to sign off. */
    fpiId: string;
    /** Whether the logged-in user holds `sign_off_fpi`. False switches the
     *  dialog into co-signature mode. */
    canSignOff: boolean;
    /** The step's authored QA assurance ("NONE" / "PASSWORD"). The buy-off IS
     *  this step's QA release, so a step authored to need a password needs one
     *  here too — otherwise an inspector signing from their own session is
     *  refused by the server with no field to comply in. The co-sign path
     *  already supplies a password and is unaffected. */
    assurance?: string;
    /** Designated part label, shown in the attestation so the signer knows
     *  exactly what they are attesting to. */
    partLabel?: string | null;
    onSigned?: () => void;
};

export function FpiSignOffDialog({
    open,
    onOpenChange,
    fpiId,
    canSignOff,
    assurance,
    partLabel,
    onSigned,
}: FpiSignOffDialogProps) {
    const needsOwnPassword = canSignOff && assurance === "PASSWORD";
    const [notes, setNotes] = useState("");
    const [ownPassword, setOwnPassword] = useState("");
    const [cosignEmail, setCosignEmail] = useState("");
    const [signature, setSignature] = useState<SignatureVerificationData>({
        signature_data: "",
        password: "",
        confirmed: false,
    });
    const [error, setError] = useState<string | null>(null);

    const passMutation = useFpiPass();

    // SignatureVerification fires onChange from a useEffect on every state
    // change — an unmemoized handler re-renders it into a loop.
    const handleSignatureChange = useCallback((d: SignatureVerificationData) => {
        setSignature(d);
    }, []);

    const reset = () => {
        setNotes("");
        setOwnPassword("");
        setCosignEmail("");
        setSignature({ signature_data: "", password: "", confirmed: false });
        setError(null);
    };

    const close = () => {
        reset();
        onOpenChange(false);
    };

    const handleConfirm = () => {
        setError(null);

        if (needsOwnPassword && !ownPassword) {
            setError("This step is authored to need your password as well.");
            return;
        }
        if (!canSignOff) {
            if (!cosignEmail.trim()) {
                setError("Enter the QA inspector's email.");
                return;
            }
            const invalid = validateSignatureVerification(signature, {
                requireSignature: true,
                requireConfirmation: true,
                requirePassword: true,
            });
            if (invalid) {
                setError(invalid);
                return;
            }
        }

        passMutation.mutate(
            {
                id: fpiId,
                notes,
                ...(canSignOff
                    ? (needsOwnPassword ? { password: ownPassword } : {})
                    : {
                        cosign_email: cosignEmail.trim(),
                        cosign_password: signature.password,
                        // Kept on the record once the password verifies (it used to
                        // be required here and then thrown away).
                        cosign_signature: signature.signature_data,
                    }),
            },
            {
                onSuccess: () => {
                    toast.success("FPI signed off — parts can now proceed.");
                    reset();
                    onOpenChange(false);
                    onSigned?.();
                },
                onError: (err: unknown) => {
                    // Surface the server's own reason. The co-sign failures are
                    // all distinguishable on purpose (throttled / wrong person /
                    // not permitted / segregation of duties), so collapsing them
                    // into "something went wrong" would waste that.
                    const resp = (err as { response?: { data?: Record<string, unknown> } })?.response;
                    const detail = apiErrorMessage(err)
                        || (resp?.data?.error as string)
                        || "Could not sign off the FPI.";
                    setError(detail);
                    toast.error(detail);
                },
            },
        );
    };

    return (
        <Dialog open={open} onOpenChange={(v) => (v ? onOpenChange(true) : close())}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Sign off First Piece Inspection</DialogTitle>
                    <DialogDescription>
                        By signing off you attest that the setup is correct and the first
                        piece{partLabel ? ` (${partLabel})` : ""} conforms, and this
                        releases the run.{" "}
                        {canSignOff
                            ? "It is recorded against your name."
                            : "It is recorded against the QA inspector's name — not the person logged in."}
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                    <div className="space-y-2">
                        <Label>Notes (optional)</Label>
                        <Textarea
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder="Inspection notes / gauges used / observations…"
                            rows={3}
                        />
                    </div>

                    {needsOwnPassword && (
                        <div className="space-y-2 border-t pt-4">
                            <Label htmlFor="fpi-own-password">Your password</Label>
                            <Input
                                id="fpi-own-password"
                                type="password"
                                autoComplete="current-password"
                                value={ownPassword}
                                onChange={(e) => setOwnPassword(e.target.value)}
                                placeholder="Re-enter your password to sign"
                            />
                            <p className="text-xs text-muted-foreground">
                                This step is authored to need a verified signature, so the
                                record says it was you and nobody else.
                            </p>
                        </div>
                    )}

                    {!canSignOff && (
                        <div className="space-y-4 border-t pt-4">
                            <p className="text-sm text-muted-foreground">
                                You aren't authorized to buy off a first piece. An
                                authorized QA inspector can sign here without logging you
                                out.
                            </p>
                            <div className="space-y-2">
                                <Label htmlFor="fpi-cosign-email">QA inspector email</Label>
                                <Input
                                    id="fpi-cosign-email"
                                    type="email"
                                    autoComplete="off"
                                    value={cosignEmail}
                                    onChange={(e) => setCosignEmail(e.target.value)}
                                    placeholder="inspector@example.com"
                                />
                            </div>
                            <SignatureVerification
                                onChange={handleSignatureChange}
                                confirmationText="I confirm this is my signature and I am authorized to buy off this first piece."
                                passwordHelpText="The QA inspector's password, to verify their identity."
                                error={error}
                            />
                        </div>
                    )}

                    {error && canSignOff && (
                        <p className="text-sm text-destructive">{error}</p>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={close}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleConfirm}
                        disabled={passMutation.isPending}
                        className="bg-green-600 hover:bg-green-700"
                    >
                        {passMutation.isPending ? "Signing off…" : "Confirm sign-off"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
