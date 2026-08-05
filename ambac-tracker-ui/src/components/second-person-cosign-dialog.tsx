/** Collects a second person's credentials at someone else's terminal.
 *
 *  The UI half of `services/core/second_person.verify_second_person`: an
 *  authorized colleague authenticates inline, is never logged in, and the act is
 *  attributed to *them*. Used wherever the person at the keyboard lacks the
 *  authority for a step they've physically arrived at — a first-piece buy-off, a
 *  MANUAL routing decision.
 *
 *  Deliberately generic: it knows nothing about what is being signed, only how
 *  to collect and hand back (email, password). The caller owns the mutation, the
 *  attestation wording, and any extra fields.
 *
 *  `FpiSignOffDialog` predates this and carries its own copy of the same form
 *  plus FPI-specific notes; worth collapsing into this once a third gate lands.
 */
import { useCallback, useState } from "react";

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
import {
    SignatureVerification,
    validateSignatureVerification,
    type SignatureVerificationData,
} from "@/components/approval/SignatureVerification";

export type SecondPersonCosignDialogProps = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    title: string;
    /** What the signer is attesting to. Shown above the credential fields. */
    description: string;
    /** Label for the email field, e.g. "Manager or lead email". */
    emailLabel: string;
    confirmationText: string;
    confirmLabel?: string;
    /** Server-side failure to surface. The co-sign errors are distinguishable on
     *  purpose (throttled / wrong person / not permitted), so pass the server's
     *  own detail through rather than collapsing them. */
    error?: string | null;
    pending?: boolean;
    onConfirm: (credentials: { email: string; password: string }) => void;
};

export function SecondPersonCosignDialog({
    open,
    onOpenChange,
    title,
    description,
    emailLabel,
    confirmationText,
    confirmLabel = "Confirm",
    error,
    pending = false,
    onConfirm,
}: SecondPersonCosignDialogProps) {
    const [email, setEmail] = useState("");
    const [signature, setSignature] = useState<SignatureVerificationData>({
        signature_data: "",
        password: "",
        confirmed: false,
    });
    const [localError, setLocalError] = useState<string | null>(null);

    // SignatureVerification fires onChange from a useEffect on every state
    // change — an unmemoized handler re-renders it into a loop.
    const handleSignatureChange = useCallback((d: SignatureVerificationData) => {
        setSignature(d);
    }, []);

    const close = () => {
        setEmail("");
        setSignature({ signature_data: "", password: "", confirmed: false });
        setLocalError(null);
        onOpenChange(false);
    };

    const confirm = () => {
        setLocalError(null);
        if (!email.trim()) {
            setLocalError(`Enter the ${emailLabel.toLowerCase()}.`);
            return;
        }
        const invalid = validateSignatureVerification(signature, {
            requireSignature: true,
            requireConfirmation: true,
            requirePassword: true,
        });
        if (invalid) {
            setLocalError(invalid);
            return;
        }
        onConfirm({ email: email.trim(), password: signature.password });
    };

    return (
        <Dialog open={open} onOpenChange={(v) => (v ? onOpenChange(true) : close())}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{title}</DialogTitle>
                    <DialogDescription>{description}</DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="cosign-email">{emailLabel}</Label>
                        <Input
                            id="cosign-email"
                            type="email"
                            autoComplete="off"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="name@example.com"
                        />
                    </div>
                    <SignatureVerification
                        onChange={handleSignatureChange}
                        confirmationText={confirmationText}
                        passwordHelpText="Their password, to verify their identity. They are not logged in here."
                        error={localError ?? error ?? null}
                    />
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={close}>
                        Cancel
                    </Button>
                    <Button onClick={confirm} disabled={pending}>
                        {pending ? "Verifying…" : confirmLabel}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
