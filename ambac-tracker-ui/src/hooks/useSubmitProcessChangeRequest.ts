import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type PcrPatch = Parameters<typeof api.api_process_change_requests_partial_update>[0];

/**
 * Submit a PCR for approval.
 *
 * Backend: `POST /api/process-change-requests/{id}/submit/` — flips the
 * PCR from DRAFT → SUBMITTED, computes the structured JSON diff from
 * the linked draft process, and stamps `submitted_by` / `submitted_at`.
 *
 * The submit body itself is empty; PCR narrative fields (title,
 * proposed_change, justification, risk_analysis, priority,
 * customer_notification_required) are written via PATCH first, which is why
 * this hook takes an optional `patch` and sends it before submitting.
 */
export function useSubmitProcessChangeRequest() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ pcrId, patch }: { pcrId: string; patch?: PcrPatch }) => {
            const headers = { "X-CSRFToken": getCookie("csrftoken") ?? "" };
            if (patch && Object.keys(patch).length > 0) {
                await api.api_process_change_requests_partial_update(patch, {
                    params: { id: pcrId },
                    headers,
                });
            }
            return api.api_process_change_requests_submit_create(undefined, {
                params: { id: pcrId },
                headers,
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "process-change-requests" });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "pcr-for-draft" });
        },
    });
}
