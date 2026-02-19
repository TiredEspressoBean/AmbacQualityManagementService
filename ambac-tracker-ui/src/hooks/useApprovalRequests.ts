import { useQuery } from "@tanstack/react-query";
import { api, schemas } from "@/lib/api/generated";
import type { z } from "zod";

export type ApprovalRequest = z.infer<typeof schemas.ApprovalRequest>;

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

export function useApprovalRequests(filters: ApprovalRequestsFilters = {}) {
    return useQuery({
        queryKey: ["approvals", "list", filters],
        queryFn: async () => {
            const response = await api.api_ApprovalRequests_list({
                approval_type: filters.approval_type,
                status: filters.status,
                requested_by: filters.requested_by,
                overdue: filters.overdue,
                search: filters.search,
                ordering: filters.ordering ?? "-requested_at",
                limit: filters.limit ?? 50,
                offset: filters.offset ?? 0,
            });
            return response;
        },
    });
}

// Hook specifically for "my submitted requests" (things I requested from others)
export function useMySubmittedRequests(userId?: number) {
    return useQuery({
        queryKey: ["approvals", "my-submitted", userId],
        queryFn: async () => {
            if (!userId) return { results: [], count: 0 };
            const response = await api.api_ApprovalRequests_list({
                requested_by: userId,
                ordering: "-requested_at",
                limit: 50,
            });
            return response;
        },
        enabled: !!userId,
    });
}
