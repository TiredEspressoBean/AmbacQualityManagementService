import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export interface ApprovalResponsePayload {
    decision: 'APPROVED' | 'REJECTED' | 'DELEGATED';
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
                { id: approvalRequestId },
                payload as any
            ),
        onSuccess: () => {
            // Invalidate related queries
            queryClient.invalidateQueries({ queryKey: ["approvals"] });
            queryClient.invalidateQueries({ queryKey: ["capas"] });
            queryClient.invalidateQueries({ queryKey: ["capa-stats"] });
        },
    });
}
