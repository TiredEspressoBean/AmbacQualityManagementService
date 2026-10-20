/** The FPI buy-off dialog — pass, fail or waive — in both of its modes.
 *
 *  `verdict` picks what is recorded: a pass releases the run; a fail keeps it held
 *  (the setup is corrected and a new first piece run); a waive releases it without
 *  the inspection, with a reason. Pass and waive meet the step's authored assurance
 *  (they release the step); a fail holds it, so it needs no password of its own.
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
import { useFpiFail, useFpiPass, useFpiWaive } from "@/hooks/useFpiRecords";
import { FpiReadings, fpiRecordOptions } from "@/components/fpi/FpiReadings";
import { useQuery } from "@tanstack/react-query";
import { useAuthUser } from "@/hooks/useAuthUser";
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
    /** What is being recorded. Defaults to a pass. */
    verdict?: FpiVerdict;
    onSigned?: () => void;
};

export type FpiVerdict = "PASS" | "FAIL" | "WAIVE";

const WAIVE_MIN = 10;

export function FpiSignOffDialog({
    open,
    onOpenChange,
    fpiId,
    canSignOff: canSignOffProp,
    assurance,
    partLabel,
    verdict = "PASS",
    onSigned,
}: FpiSignOffDialogProps) {
    // A fail holds the run, so it isn't held to the release bar; pass and waive are.
    // Whoever signed the first piece's substeps can't buy it off (segregation of
    // duties). Know it before the click: switch to the co-sign path and say why,
    // rather than refusing after "Confirm".
    const { data: me } = useAuthUser();
    const { data: record } = useQuery({ ...fpiRecordOptions(fpiId), enabled: open });
    const selfSigned = !!me && (record?.first_piece_signer_ids ?? []).includes(me.pk);
    const canSignOff = canSignOffProp && !selfSigned;
    const needsOwnPassword = canSignOff && assurance === "PASSWORD" && verdict !== "FAIL";
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
    const failMutation = useFpiFail();
    const waiveMutation = useFpiWaive();
    const pending = passMutation.isPending || failMutation.isPending || waiveMutation.isPending;

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

        if (verdict === "FAIL" && !notes.trim()) {
            setError("Say what was wrong, so the setup can be corrected.");
            return;
        }
        if (verdict === "WAIVE" && notes.trim().length < WAIVE_MIN) {
            setError(`Give the reason for waiving (at least ${WAIVE_MIN} characters).`);
            return;
        }
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

        const signer = canSignOff
            ? (needsOwnPassword ? { password: ownPassword } : {})
            : {
                cosign_email: cosignEmail.trim(),
                cosign_password: signature.password,
                // Kept on the record once the password verifies (it used to
                // be required here and then thrown away).
                cosign_signature: signature.signature_data,
            };
        const callbacks = {
                onSuccess: () => {
                    toast.success(DONE[verdict]);
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
                        || "Could not record the FPI verdict.";
                    // Shown inline in the dialog; a toast as well said it twice.
                    setError(detail);
                },
            };
        if (verdict === "FAIL") {
            failMutation.mutate({ id: fpiId, notes: notes.trim(), ...signer }, callbacks);
        } else if (verdict === "WAIVE") {
            waiveMutation.mutate({ id: fpiId, reason: notes.trim(), ...signer }, callbacks);
        } else {
            passMutation.mutate({ id: fpiId, notes, ...signer }, callbacks);
        }
    };

    return (
        <Dialog open={open} onOpenChange={(v) => (v ? onOpenChange(true) : close())}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{TITLE[verdict]}</DialogTitle>
                    <DialogDescription>
                        {verdict === "PASS" && <>
                            By signing off you attest that the setup is correct and the first
                            piece{partLabel ? ` (${partLabel})` : ""} conforms, and this
                            releases the run.{" "}
                        </>}
                        {verdict === "FAIL" && <>
                            The setup did not pass{partLabel ? ` (first piece ${partLabel})` : ""}. The
                            run stays held; correct the setup and run a new first piece for
                            re-inspection.{" "}
                        </>}
                        {verdict === "WAIVE" && <>
                            Waiving releases the run without a first-piece buy-off. Say why — it
                            stays on the record.{" "}
                        </>}
                        {canSignOff
                            ? "It is recorded against your name."
                            : "It is recorded against the QA inspector's name — not the person logged in."}
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                    <FpiReadings fpiId={fpiId} />
                    <div className="space-y-2">
                        <Label>{NOTES_LABEL[verdict]}</Label>
                        <Textarea
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder={NOTES_PLACEHOLDER[verdict]}
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

                    {selfSigned && (
                        <p className="rounded-md border border-amber-500/40 bg-amber-500/10 p-2 text-sm">
                            You signed this first piece&rsquo;s inspection, so another qualified
                            inspector must sign — they can sign here below.
                        </p>
                    )}

                    {!canSignOff && (
                        <div className="space-y-4 border-t pt-4">
                            {!selfSigned && (
                                <p className="text-sm text-muted-foreground">
                                    You aren't authorized to buy off a first piece. An
                                    authorized QA inspector can sign here without logging you
                                    out.
                                </p>
                            )}
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
                                confirmationText={`I confirm this is my signature and I am authorized to ${verdict === "PASS" ? "buy off" : verdict === "FAIL" ? "fail" : "waive"} this first piece.`}
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
                        disabled={pending}
                        variant={verdict === "FAIL" ? "destructive" : "default"}
                        className={verdict === "PASS" ? "bg-green-600 hover:bg-green-700" : undefined}
                    >
                        {pending ? "Recording…" : CONFIRM[verdict]}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

const TITLE: Record<FpiVerdict, string> = {
    PASS: "Sign off First Piece Inspection",
    FAIL: "Fail First Piece Inspection",
    WAIVE: "Waive First Piece Inspection",
};
const CONFIRM: Record<FpiVerdict, string> = {
    PASS: "Confirm sign-off",
    FAIL: "Record failure",
    WAIVE: "Waive FPI",
};
const DONE: Record<FpiVerdict, string> = {
    PASS: "FPI signed off — parts can now proceed.",
    FAIL: "FPI failed — correct the setup and re-run the first piece.",
    WAIVE: "FPI requirement waived.",
};
const NOTES_LABEL: Record<FpiVerdict, string> = {
    PASS: "Notes (optional)",
    FAIL: "Reason / findings",
    WAIVE: "Reason for waiving",
};
const NOTES_PLACEHOLDER: Record<FpiVerdict, string> = {
    PASS: "Inspection notes / gauges used / observations…",
    FAIL: "What was out of spec / what needs correcting…",
    WAIVE: "Why this first piece doesn't need inspecting (e.g. identical setup re-run, customer concession)…",
};
