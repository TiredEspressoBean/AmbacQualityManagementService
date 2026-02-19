import { useQuery } from "@tanstack/react-query";
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
    requested_by: string;
    requested_by_info?: {
        id: string;
        username: string;
        full_name?: string;
    };
    requested_at: string;
    due_date: string | null;
    reason?: string;
    notes?: string;
}

// Response can be either an array or paginated result
type MyPendingResponse = PendingApproval[] | { results: PendingApproval[]; count: number };

export function useMyPendingApprovals() {
    return useQuery({
        queryKey: ["approvals", "my-pending"],
        queryFn: async () => {
            const response = await api.api_ApprovalRequests_my_pending_list() as MyPendingResponse;
            // Normalize response: return array whether paginated or not
            return Array.isArray(response) ? response : response.results;
        },
    });
}
