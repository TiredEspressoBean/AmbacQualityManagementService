import { useQuery, queryOptions } from "@tanstack/react-query";
import { api, type DecisionEnum } from "@/lib/api/generated";

export interface ApprovalResponse {
    id: string;
    approver: string;
    approver_info?: {
        id: string;
        username: string;
        full_name?: string;
    };
    decision: DecisionEnum;
    decision_display: string;
    comments?: string;
    signature_data?: string;
    signature_meaning?: string;
    decision_date: string;  // When the response was submitted
    delegated_to?: string;
    delegated_to_info?: {
        id: string;
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
    content_type: string;
    object_id: string;
    content_object_display?: string;
    requested_by: string;
    requested_by_info?: {
        id: string;
        username: string;
        full_name?: string;
    };
    requested_at: string;
    completed_at?: string;
    due_date: string | null;
    reason?: string;
    notes?: string;
    is_overdue?: boolean;
    required_approvers: string[];
    optional_approvers: string[];
    approver_groups: string[];
    responses: ApprovalResponse[];
    threshold?: number;
}

export const approvalRequestOptions = (id: string) => queryOptions<ApprovalRequest>({
    queryKey: ["approvals", "detail", id] as const,
    // eslint-disable-next-line local/no-double-cast-via-unknown -- local ApprovalRequest interface predates schema generation; fields like required_approvers differ in shape from generated type
    queryFn: () => api.api_ApprovalRequests_retrieve({ params: { id } }) as unknown as Promise<ApprovalRequest>,
});

export function useApprovalRequest(id: string | undefined) {
    return useQuery({
        ...approvalRequestOptions(id!),
        enabled: id !== undefined,
    });
}
