import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { useContentTypeMapping } from "./useContentTypes";

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
    decision_date: string;
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
    required_approvers_info?: Array<{
        id: string;
        username: string;
        full_name?: string;
    }>;
    optional_approvers: string[];
    approver_groups: string[];
    approver_groups_info?: Array<{
        id: string;
        name: string;
    }>;
    responses: ApprovalResponse[];
    threshold?: number;
}

interface PaginatedResponse {
    count: number;
    next: string | null;
    previous: string | null;
    results: ApprovalRequest[];
}

/**
 * Hook to fetch the approval request(s) for a specific Document.
 * Returns the most recent pending or completed approval request.
 */
export function useDocumentApprovalRequest(documentId: string | undefined) {
    const { getContentTypeId, isLoading: contentTypesLoading } = useContentTypeMapping();
    const documentsContentTypeId = getContentTypeId('documents');

    return useQuery({
        queryKey: ["approvals", "document", documentId, documentsContentTypeId],
        queryFn: async () => {
            if (!documentsContentTypeId) {
                throw new Error("Documents content type not found");
            }
            const response = await api.api_ApprovalRequests_list({
                queries: {
                    content_type: documentsContentTypeId,
                    object_id: documentId!,
                    ordering: '-requested_at',
                    limit: 10,
                }
            }) as PaginatedResponse;

            return response.results;
        },
        enabled: documentId !== undefined && !!documentsContentTypeId && !contentTypesLoading,
    });
}
