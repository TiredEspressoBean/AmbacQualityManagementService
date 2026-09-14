import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type ApprovalResponseDecisionEnum } from "@/lib/api/generated";

export interface ApprovalResponsePayload {
    decision: ApprovalResponseDecisionEnum;
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
        },
    });
}
