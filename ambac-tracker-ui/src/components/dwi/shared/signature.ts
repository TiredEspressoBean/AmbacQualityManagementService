/**
 * Shared signature payload shape used by `AttestationCheckpoint`
 * (signature mode) and `InspectionSignatures`. One stored type means the
 * operator-runtime persistence layer can route any captured signature
 * through the same audit path (write a `QualityReportPersonnel` row with
 * `signed_at` set when it's an inspection-point substep, or a
 * `SubstepResponse` otherwise).
 *
 * Why no canvas image yet: UQMES doesn't target food / drug / medical, so
 * 21 CFR Part 11-grade e-signature with a captured stroke isn't required
 * for the first cut. We capture user + timestamp so the audit trail still
 * answers "who signed, when?" — and the schema accommodates a `data_uri`
 * field later when a canvas widget is dropped in.
 */
export type SignaturePayload = {
    user_id: number;
    username: string;
    signed_at: string; // ISO timestamp
    /** Reserved for a future SignatureCanvas integration. Base64 PNG data
     *  URI when the canvas captures a stroke; undefined otherwise. */
    data_uri?: string;
};

/** Type-guard for when something is read from `OperatorResponseContext`. */
export function isSignaturePayload(v: unknown): v is SignaturePayload {
    return (
        typeof v === "object" &&
        v !== null &&
        typeof (v as SignaturePayload).user_id === "number" &&
        typeof (v as SignaturePayload).signed_at === "string"
    );
}
