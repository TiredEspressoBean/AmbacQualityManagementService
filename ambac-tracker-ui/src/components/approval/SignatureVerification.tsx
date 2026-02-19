import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { PasswordInput } from "@/components/ui/password-input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { SignatureCanvas } from "./SignatureCanvas";

export interface SignatureVerificationData {
    signature_data: string;
    password: string;
    confirmed: boolean;
}

export interface SignatureVerificationProps {
    /** Called when any value changes. Returns current state. */
    onChange: (data: SignatureVerificationData) => void;
    /** Optional initial values */
    initialData?: Partial<SignatureVerificationData>;
    /** Height of signature canvas (default: 120) */
    signatureHeight?: number;
    /** Custom confirmation text */
    confirmationText?: string;
    /** Custom password help text */
    passwordHelpText?: string;
    /** Error message to display */
    error?: string | null;
    /** Whether the component is disabled */
    disabled?: boolean;
    /** Whether to show the required asterisk on labels */
    required?: boolean;
}

/**
 * Reusable signature verification component that bundles:
 * - Signature canvas
 * - Confirmation checkbox
 * - Password verification
 *
 * Used for approvals, task completion, and other identity-verified actions.
 */
export function SignatureVerification({
    onChange,
    initialData,
    signatureHeight = 120,
    confirmationText = "I confirm this is my signature and I am authorized to perform this action.",
    passwordHelpText = "Your password is required to verify your identity.",
    error,
    disabled = false,
    required = true,
}: SignatureVerificationProps) {
    const [signatureData, setSignatureData] = useState(initialData?.signature_data || "");
    const [confirmed, setConfirmed] = useState(initialData?.confirmed || false);
    const [password, setPassword] = useState(initialData?.password || "");

    // Notify parent of changes
    useEffect(() => {
        onChange({
            signature_data: signatureData,
            password,
            confirmed,
        });
    }, [signatureData, password, confirmed, onChange]);

    return (
        <div className="space-y-4">
            {/* Signature Canvas */}
            <div className="space-y-2">
                <Label>
                    Signature {required && <span className="text-destructive">*</span>}
                </Label>
                <SignatureCanvas
                    value={signatureData}
                    onChange={setSignatureData}
                    height={signatureHeight}
                    disabled={disabled}
                />
            </div>

            {/* Confirmation Checkbox */}
            <div className="flex items-start space-x-2">
                <Checkbox
                    id="signature-confirmation"
                    checked={confirmed}
                    onCheckedChange={(checked) => setConfirmed(checked === true)}
                    disabled={disabled}
                />
                <Label
                    htmlFor="signature-confirmation"
                    className="text-sm leading-tight cursor-pointer"
                >
                    {confirmationText}
                </Label>
            </div>

            {/* Password Verification */}
            <div className="space-y-2">
                <Label htmlFor="signature-password">
                    Password {required && <span className="text-destructive">*</span>}
                </Label>
                <PasswordInput
                    id="signature-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password to verify identity"
                    disabled={disabled}
                />
                <p className="text-xs text-muted-foreground">
                    {passwordHelpText}
                </p>
            </div>

            {/* Error Display */}
            {error && (
                <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}
        </div>
    );
}

/**
 * Validates signature verification data.
 * Returns an error message if invalid, or null if valid.
 */
export function validateSignatureVerification(
    data: SignatureVerificationData,
    options?: { requireSignature?: boolean; requireConfirmation?: boolean; requirePassword?: boolean }
): string | null {
    const {
        requireSignature = true,
        requireConfirmation = true,
        requirePassword = true,
    } = options || {};

    if (requireSignature && !data.signature_data) {
        return "Signature is required";
    }
    if (requireConfirmation && !data.confirmed) {
        return "Please confirm your signature";
    }
    if (requirePassword && !data.password) {
        return "Password is required for identity verification";
    }
    return null;
}
