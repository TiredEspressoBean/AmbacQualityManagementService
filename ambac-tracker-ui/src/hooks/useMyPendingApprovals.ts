import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export interface PendingApproval {
    id: string;
    approval_number: string;
    approval_type: string;
    approval_type_display: string;
    status: string;
    status_display: string;
    content_type: string;
    object_id: string;
    content_object_info?: {
        type: string;
        id: string;
        str?: string;
    };
    content_object_display?: string | null;
    requested_by: string;
    requested_by_info?: {
        id: string;
        username: string;
        full_name?: string;
    };
    requested_at: string;
    due_date: string | null;
    is_overdue?: boolean;
    reason?: string;
    notes?: string;
}

// Response can be either an array or paginated result
type MyPendingResponse = PendingApproval[] | { results: PendingApproval[]; count: number };

export const myPendingApprovalsOptions = () => queryOptions({
    queryKey: ["approvals", "my-pending"] as const,
    queryFn: async (): Promise<PendingApproval[]> => {
        // eslint-disable-next-line local/no-double-cast-via-unknown -- api_ApprovalRequests_my_pending_list returns a custom action response not typed in the schema
        const response = await api.api_ApprovalRequests_my_pending_list() as unknown as MyPendingResponse;
        // Normalize response: return array whether paginated or not
        return Array.isArray(response) ? response : response.results;
    },
});

export function useMyPendingApprovals() {
    return useQuery(myPendingApprovalsOptions());
}
