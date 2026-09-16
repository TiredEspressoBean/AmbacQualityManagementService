import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { useContentTypeMapping } from "./useContentTypes";

/** A row from the approvals list, narrowed to the fields this surface renders.
 *
 *  Derived from the contract rather than hand-written. The hand-written version
 *  declared `content_type: string` where the API sends a number, and the filter
 *  below compared it with `=== String(id)` -- never true, so this hook returned
 *  an empty list no matter how many document approvals were pending. Both sides
 *  came from the same wrong assumption, so neither looked out of place. */
export type PendingDocumentApproval = Awaited<
    ReturnType<typeof api.api_ApprovalRequests_my_pending_list>
>["results"][number];

export const documentsPendingApprovalOptions = (documentsContentTypeId: number | undefined) => queryOptions({
    queryKey: ["documents", "pending-approval", documentsContentTypeId] as const,
    queryFn: async () => {
        // The response is typed (PaginatedApprovalRequestList) -- the cast that
        // used to be here claimed otherwise, and hid the mismatch below.
        const response = await api.api_ApprovalRequests_my_pending_list();

        // Numeric comparison: content_type is an integer pk on both sides.
        return response.results.filter(
            (approval) => approval.content_type === documentsContentTypeId,
        );
    },
});

/**
 * Hook to fetch documents pending the current user's approval.
 * Uses the ApprovalRequests my-pending endpoint filtered by document content type.
 */
export function useDocumentsPendingApproval() {
    const { getContentTypeId, isLoading: ctLoading } = useContentTypeMapping();
    const documentsContentTypeId = getContentTypeId('documents');

    return useQuery({
        ...documentsPendingApprovalOptions(documentsContentTypeId),
        enabled: !ctLoading && !!documentsContentTypeId,
    });
}
