import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type ApprovalResponseDecisionEnum } from "@/lib/api/generated";

export interface ApprovalResponsePayload {
    /** An answer — WITHDRAWN is set only by taking one back (withdraw-response). */
    decision: Exclude<ApprovalResponseDecisionEnum, "WITHDRAWN">;
    comments?: string;
    signature_data?: string;
    signature_meaning?: string;
    password?: string;
    delegate_to?: number;
}

// Invalidation-only helpers (not real queryOptions — no queryFn needed).
const approvalsKeyOptions = () => ({ queryKey: ["approvals"] as const });
const capasKeyOptions = () => ({ queryKey: ["capas"] as const });
const capaStatsKeyOptions = () => ({ queryKey: ["capa-stats"] as const });
// Prefixes of retrieveCapaOptions / retrieveDocumentOptions (["capa", id] / ["document", id]).
const capaDetailKeyOptions = () => ({ queryKey: ["capa"] as const });
const documentDetailKeyOptions = () => ({ queryKey: ["document"] as const });

export function useSubmitApprovalResponse(approvalRequestId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (payload: ApprovalResponsePayload) =>
            api.api_ApprovalRequests_submit_response_create(
                payload,
                { params: { id: approvalRequestId } },
            ),
        onSuccess: () => {
            // Invalidate related queries
            queryClient.invalidateQueries(approvalsKeyOptions());
            queryClient.invalidateQueries(capasKeyOptions());
            queryClient.invalidateQueries(capaStatsKeyOptions());
            // The approved object's own detail carries approval_status (the tab's badge
            // and "Awaiting approval" alert read it) — ["capa", id] / ["document", id].
            // Only the list keys were refreshed, so the page stayed Pending until reload.
            queryClient.invalidateQueries(capaDetailKeyOptions());
            queryClient.invalidateQueries(documentDetailKeyOptions());
        },
    });
}
