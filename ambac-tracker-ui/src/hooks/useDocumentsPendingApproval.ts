import { useQuery } from "@tanstack/react-query";
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

/**
 * Hook to fetch documents pending the current user's approval.
 * Uses the ApprovalRequests my-pending endpoint filtered by document content type.
 */
export function useDocumentsPendingApproval() {
    const { getContentTypeId, isLoading: ctLoading } = useContentTypeMapping();
    const documentsContentTypeId = getContentTypeId('documents');

    return useQuery({
        queryKey: ["documents", "pending-approval"],
        queryFn: async () => {
            // Get all pending approvals and filter to documents
            const response = await api.api_ApprovalRequests_my_pending_retrieve() as any;
            const results = response?.results || response || [];

            // Filter to only document approvals
            return results.filter((approval: PendingDocumentApproval) =>
                approval.content_type === documentsContentTypeId
            );
        },
        enabled: !ctLoading && !!documentsContentTypeId,
    });
}
