import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export interface ApprovalResponse {
    id: string;
    approver: string;
    approver_info?: {
        id: string;
        username: string;
        full_name?: string;
    };
    decision: 'APPROVED' | 'REJECTED' | 'DELEGATED';
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

export function useApprovalRequest(id: string | undefined) {
    return useQuery({
        queryKey: ["approvals", "detail", id],
        queryFn: () => api.api_ApprovalRequests_retrieve({ params: { id: id! } }) as Promise<ApprovalRequest>,
        enabled: id !== undefined,
    });
}
