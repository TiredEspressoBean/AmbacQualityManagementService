/**
 * Ask for a verified signature (drawn signature + the signer's own password) and
 * wait for it — a substep authored `requires_signature` is refused by the server
 * without one. `request(meaning)` resolves to the signature, or null if the
 * operator cancels; render `dialog` once wherever the hook is used.
 *
 * Promise-shaped so a submit loop can collect every signature up front, in order,
 * and abandon the whole completion on a cancel (nothing is written).
 */
import { useCallback, useRef, useState, type ReactNode } from "react";
import { PenLine } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
    SignatureVerification,
    validateSignatureVerification,
    type SignatureVerificationData,
} from "@/components/approval/SignatureVerification";

export type VerifiedSignature = { signature_data: string; password: string };
/** A re-ask after the server refused the password: the drawn signature is kept,
 *  only the password is entered again, and the server's reason is shown. */
export type SignatureRetry = { signature_data: string; reason: string };
export type RequestSignature = (
    meaning: string, retry?: SignatureRetry,
) => Promise<VerifiedSignature | null>;

const EMPTY: SignatureVerificationData = { signature_data: "", password: "", confirmed: false };

export function useSignaturePrompt(): { request: RequestSignature; dialog: ReactNode } {
    const [meaning, setMeaning] = useState<string | null>(null);
    const [initial, setInitial] = useState<SignatureVerificationData>(EMPTY);
    const [data, setData] = useState<SignatureVerificationData>(EMPTY);
    const [error, setError] = useState<string | null>(null);
    // A fresh pad per request: closing one prompt and opening the next can land in
    // a single render, which would otherwise reuse the previous pad's state.
    const [requestId, setRequestId] = useState(0);
    // The pending request's resolver; a ref so settling it never re-renders.
    const settle = useRef<((v: VerifiedSignature | null) => void) | null>(null);

    const request = useCallback<RequestSignature>((m, retry) => new Promise((resolve) => {
        settle.current?.(null); // a stray earlier prompt counts as cancelled
        settle.current = resolve;
        const start = retry
            ? { signature_data: retry.signature_data, password: "", confirmed: true }
            : EMPTY;
        setInitial(start);
        setData(start);
        setError(retry?.reason ?? null);
        setRequestId((n) => n + 1);
        setMeaning(m);
    }), []);

    const finish = (v: VerifiedSignature | null) => {
        settle.current?.(v);
        settle.current = null;
        setMeaning(null);
    };

    // SignatureVerification fires onChange from an effect; a stable handler
    // keeps it from re-rendering into a loop.
    const onChange = useCallback((d: SignatureVerificationData) => setData(d), []);

    const sign = () => {
        const problem = validateSignatureVerification(data);
        if (problem) {
            setError(problem);
            return;
        }
        finish({ signature_data: data.signature_data, password: data.password });
    };

    const dialog = (
        <Dialog open={meaning !== null} onOpenChange={(open) => { if (!open) finish(null); }}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <PenLine className="h-5 w-5" />
                        Sign: {meaning}
                    </DialogTitle>
                    <DialogDescription>
                        This step needs your verified signature. Sign, then enter your own
                        password — it records that you, and nobody else, signed it.
                    </DialogDescription>
                </DialogHeader>
                {meaning !== null && (
                    <SignatureVerification
                        key={requestId}
                        initialData={initial}
                        onChange={onChange}
                        error={error}
                        required
                    />
                )}
                <DialogFooter>
                    <Button variant="outline" onClick={() => finish(null)}>Cancel</Button>
                    <Button onClick={sign}>Sign</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );

    return { request, dialog };
}
