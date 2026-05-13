import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { useContentTypeMapping } from "./useContentTypes";

export interface PendingDocumentApproval {
    id: string;
    approval_number: string;
    approval_type: string;
    approval_type_display: string;
    status: string;
    content_type: string;
    object_id: string;
    content_object_display?: string;
    requested_at: string;
    due_date: string | null;
    is_overdue?: boolean;
}

export const documentsPendingApprovalOptions = (documentsContentTypeId: number | undefined) => queryOptions({
    queryKey: ["documents", "pending-approval", documentsContentTypeId] as const,
    queryFn: async () => {
        // Get all pending approvals and filter to documents
        // eslint-disable-next-line local/no-as-any -- api_ApprovalRequests_my_pending_list has untyped response; shape is normalized below
        const response = await api.api_ApprovalRequests_my_pending_list() as any;
        const results = response?.results || response || [];

        // Filter to only document approvals
        return results.filter((approval: PendingDocumentApproval) =>
            approval.content_type === String(documentsContentTypeId)
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
