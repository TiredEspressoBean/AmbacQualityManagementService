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
 *  No drawn signature: none of these acts records one, so a pad here would collect a
 *  signature nobody keeps. A first-piece buy-off does record it, and draws it in
 *  `FpiSignOffDialog` (signature only where the act requires one — NCR review P3).
 */
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
    const [password, setPassword] = useState("");
    const [attested, setAttested] = useState(false);
    const [localError, setLocalError] = useState<string | null>(null);

    const close = () => {
        setEmail("");
        setPassword("");
        setAttested(false);
        setLocalError(null);
        onOpenChange(false);
    };

    const confirm = () => {
        setLocalError(null);
        if (!email.trim()) {
            setLocalError(`Enter the ${emailLabel.toLowerCase()}.`);
            return;
        }
        if (!password) {
            setLocalError("Enter their password.");
            return;
        }
        if (!attested) {
            setLocalError("They must confirm the statement.");
            return;
        }
        onConfirm({ email: email.trim(), password });
    };

    const shown = localError ?? error ?? null;
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
                    <div className="space-y-2">
                        <Label htmlFor="cosign-password">Password</Label>
                        <Input
                            id="cosign-password"
                            type="password"
                            autoComplete="off"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                        <p className="text-xs text-muted-foreground">
                            Their password, to verify their identity. They are not logged in here.
                        </p>
                    </div>
                    <div className="flex items-start gap-2">
                        <Checkbox id="cosign-attest" checked={attested}
                                  onCheckedChange={(v) => setAttested(v === true)} />
                        <Label htmlFor="cosign-attest" className="text-sm font-normal leading-snug">
                            {confirmationText}
                        </Label>
                    </div>
                    {shown && <p className="text-sm text-destructive">{shown}</p>}
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
