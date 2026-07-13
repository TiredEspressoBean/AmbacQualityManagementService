/** Claim a group-routed approval (Accept → mine): self-assigns the caller as
 *  its approver, moving it from the group's shared queue to their pending list. */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useClaimApproval() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (approvalId: string) =>
            api.api_ApprovalRequests_claim_create(undefined as never, { params: { id: approvalId } }),
        onSuccess: () => {
            // Covers ["approvals", "claimable"] and ["approvals", "my-pending"].
            queryClient.invalidateQueries({ queryKey: ["approvals"] });
        },
    });
}
