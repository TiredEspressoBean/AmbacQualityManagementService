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

export function useSubmitApprovalResponse(approvalRequestId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (payload: ApprovalResponsePayload) =>
            api.api_ApprovalRequests_submit_response_create(
                payload as never,
                { params: { id: approvalRequestId } },
            ),
        onSuccess: () => {
            // Invalidate related queries
            queryClient.invalidateQueries({ queryKey: ["approvals"] });
            queryClient.invalidateQueries({ queryKey: ["capas"] });
            queryClient.invalidateQueries({ queryKey: ["capa-stats"] });
        },
    });
}
