import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

/**
 * Submit a PCR for approval.
 *
 * Backend: `POST /api/process-change-requests/{id}/submit/` — flips the
 * PCR from DRAFT → SUBMITTED, computes the structured JSON diff from
 * the linked draft process, and stamps `submitted_by` / `submitted_at`.
 *
 * The submit body itself is empty; PCR narrative fields (title,
 * proposed_change, justification, risk_analysis, priority,
 * customer_notification_required) are written via PATCH before submit.
 * The modal in the UI saves narrative fields with a PATCH, then calls
 * this hook with no extra payload.
 *
 * Raw fetch (not Zodios) because the submit action's response is not
 * always parseable by the auto-inferred Zodios schema during the
 * transition (status flips mid-call).
 */
export function useSubmitProcessChangeRequest() {
    const queryClient = useQueryClient();
    return useMutation<unknown, Error, { pcrId: string; patch?: Record<string, unknown> }>({
        mutationFn: async ({ pcrId, patch }) => {
            const csrf = getCookie("csrftoken") ?? "";
            if (patch && Object.keys(patch).length > 0) {
                const pr = await fetch(`/api/process-change-requests/${pcrId}/`, {
                    method: "PATCH",
                    credentials: "include",
                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
                    body: JSON.stringify(patch),
                });
                if (!pr.ok) {
                    const t = await pr.text().catch(() => "");
                    throw new Error(t || `Patch failed: HTTP ${pr.status}`);
                }
            }
            const r = await fetch(`/api/process-change-requests/${pcrId}/submit/`, {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
                body: "{}",
            });
            if (!r.ok) {
                const t = await r.text().catch(() => "");
                throw new Error(t || `HTTP ${r.status}`);
            }
            return r.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["process-change-requests"] });
            queryClient.invalidateQueries({ queryKey: ["pcr-for-draft"] });
        },
    });
}
