import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

export type ApprovalRequest = Schema<"ApprovalRequest">;
type PaginatedApprovalRequestList = Schema<"PaginatedApprovalRequestList">;

export interface ApprovalRequestsFilters {
    approval_type?: string;
    status?: string;
    requested_by?: number;
    overdue?: boolean;
    search?: string;
    ordering?: string;
    limit?: number;
    offset?: number;
}

export const approvalRequestsOptions = (filters: ApprovalRequestsFilters = {}) => queryOptions<PaginatedApprovalRequestList>({
    queryKey: ["approvals", "list", filters] as const,
    queryFn: async () => {
        const response = await api.api_ApprovalRequests_list({
            queries: {
                approval_type: filters.approval_type,
                status: filters.status,
                requested_by: filters.requested_by,
                overdue: filters.overdue,
                search: filters.search,
                ordering: filters.ordering ?? "-requested_at",
                limit: filters.limit ?? 50,
                offset: filters.offset ?? 0,
            },
        });
        // eslint-disable-next-line local/no-double-cast-via-unknown -- generated api returns slightly different shape than Schema<"PaginatedApprovalRequestList">; runtime types match
        return response as unknown as PaginatedApprovalRequestList;
    },
});

export function useApprovalRequests(filters: ApprovalRequestsFilters = {}) {
    return useQuery({ ...approvalRequestsOptions(filters) });
}

// Hook specifically for "my submitted requests" (things I requested from others)
export const mySubmittedRequestsOptions = (userId?: number) => queryOptions({
    queryKey: ["approvals", "my-submitted", userId] as const,
    queryFn: async () => {
        if (!userId) return { results: [], count: 0 };
        const response = await api.api_ApprovalRequests_list({
            queries: {
                requested_by: userId,
                ordering: "-requested_at",
                limit: 50,
            },
        });
        return response;
    },
});

export function useMySubmittedRequests(userId?: number) {
    return useQuery({ ...mySubmittedRequestsOptions(userId), enabled: !!userId });
}
