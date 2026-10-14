/** Submitting a substep that may carry a verified signature (see
 *  components/dwi/useSignaturePrompt). Shared by the player's completion paths and
 *  the batch panel. */
import type { Substep } from "@/hooks/useSubsteps";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import type { RequestSignature, VerifiedSignature } from "@/components/dwi/useSignaturePrompt";

// The server's password refusals (services/core/second_person.verify_own_password).
// A throttle refusal is deliberately not here: re-asking would only extend it.
const PASSWORD_REFUSALS = ["That password isn't right.", "Enter your password to sign."];

/** Submit one substep; if the server refuses a signature's PASSWORD, ask again —
 *  same drawn signature, password only — and retry. Returns null when recorded,
 *  or why it wasn't (the refusal, or the operator cancelling the re-ask). */
export async function submitSignedSubstep(
    substep: Substep,
    signature: VerifiedSignature | undefined,
    requestSignature: RequestSignature,
    send: (fields: Record<string, string>) => Promise<unknown>,
): Promise<string | null> {
    let sig = signature;
    for (;;) {
        try {
            await send(sig ? { signature_data: sig.signature_data, password: sig.password,
                               signature_meaning: substep.title ?? "" } : {});
            return null;
        } catch (err) {
            const reason = apiErrorMessage(err) ?? "failed";
            if (!sig || !PASSWORD_REFUSALS.some((m) => reason.includes(m))) return reason;
            const again = await requestSignature(substep.title ?? "this substep",
                { signature_data: sig.signature_data, reason });
            if (again === null) return "signature cancelled";
            sig = again;
        }
    }
}
