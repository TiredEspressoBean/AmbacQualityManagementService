/** Approvals the current user can claim: pending, routed to one of their
 *  groups, not yet claimed or individually assigned (the Veeva
 *  "available to claim" queue — prevents group-routed approvals rotting while
 *  everyone assumes someone else has them). */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export type ClaimableApproval = {
    id: string;
    approval_number?: string | null;
    approval_type?: string | null;
    reason?: string | null;
    due_date?: string | null;
    requested_at?: string | null;
};

export function useClaimableApprovals() {
    return useQuery({
        queryKey: ["approvals", "claimable"] as const,
        queryFn: () =>
            api.api_ApprovalRequests_claimable_list({ queries: { limit: 10 } } as never) as Promise<{
                results?: ClaimableApproval[];
            }>,
        staleTime: 15_000,
        select: (resp) => resp.results ?? [],
    });
}
