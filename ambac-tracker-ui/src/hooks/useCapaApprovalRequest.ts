import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { useContentTypeMapping } from "./useContentTypes";

export interface ApprovalResponse {
    id: string;
    approver: number;
    approver_info?: {
        id: number;
        username: string;
        full_name?: string;
    };
    decision: 'APPROVED' | 'REJECTED' | 'DELEGATED';
    decision_display: string;
    comments?: string;
    signature_data?: string;
    signature_meaning?: string;
    decision_date: string;  // When the response was submitted
    delegated_to?: number;
    delegated_to_info?: {
        id: number;
        username: string;
        full_name?: string;
    };
}

export interface ApprovalRequest {
    id: string;
    approval_number: string;
    approval_type: string;
    approval_type_display: string;
    status: string;
    status_display: string;
    flow_type: string;
    flow_type_display: string;
    content_type: number;
    object_id: string;
    content_object_display?: string;
    requested_by: number;
    requested_by_info?: {
        id: number;
        username: string;
        full_name?: string;
    };
    requested_at: string;
    completed_at?: string;
    due_date: string | null;
    reason?: string;
    notes?: string;
    is_overdue?: boolean;
    required_approvers: number[];
    required_approvers_info?: Array<{
        id: number;
        username: string;
        full_name?: string;
    }>;
    optional_approvers: number[];
    approver_groups: number[];
    approver_groups_info?: Array<{
        id: number;
        name: string;
    }>;
    responses: ApprovalResponse[];
    threshold?: number;
}

interface PaginatedResponse {
    count: number;
    next: string | null;
    previous: string | null;
    results: ApprovalRequest[];
}

/**
 * Hook to fetch the approval request(s) for a specific CAPA.
 * Returns the most recent pending or completed approval request.
 */
export function useCapaApprovalRequest(capaId: string | undefined) {
    const { getContentTypeId, isLoading: contentTypesLoading } = useContentTypeMapping();
    const capaContentTypeId = getContentTypeId('capa');

    return useQuery({
        queryKey: ["approvals", "capa", capaId, capaContentTypeId],
        queryFn: async () => {
            if (!capaContentTypeId) {
                throw new Error("CAPA content type not found");
            }
            const response = await api.api_ApprovalRequests_list({
                queries: {
                    content_type: capaContentTypeId,
                    object_id: capaId!,
                    ordering: '-requested_at',
                    limit: 10,
                }
            }) as PaginatedResponse;

            // Return the most recent approval request (usually pending or the last completed)
            return response.results;
        },
        enabled: capaId !== undefined && !!capaContentTypeId && !contentTypesLoading,
    });
}

/**
 * Hook to check if the current user can respond to a CAPA's approval request.
 * Returns the approval request ID if user can respond, null otherwise.
 */
export function useCanRespondToCapaApproval(capaId: string | undefined) {
    const { data: approvalRequests, isLoading } = useCapaApprovalRequest(capaId);

    // Find the pending approval request (if any)
    const pendingRequest = approvalRequests?.find(req => req.status === 'PENDING');

    return {
        canRespond: !!pendingRequest,
        approvalRequest: pendingRequest,
        isLoading,
    };
}
