import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { useContentTypeMapping } from "./useContentTypes";
import type { ApprovalRequest } from "./useDocumentApprovalRequest";

interface PaginatedResponse {
    count: number;
    next: string | null;
    previous: string | null;
    results: ApprovalRequest[];
}

export const approvalRequestsForOptions = (
    contentTypeId: number | undefined,
    objectId: string | undefined,
) => queryOptions({
    queryKey: ["approvals", "for-object", contentTypeId, objectId] as const,
    queryFn: async () => {
        if (!contentTypeId) {
            throw new Error("Content type not resolved");
        }
        // eslint-disable-next-line local/no-double-cast-via-unknown -- local ApprovalRequest interface has narrower types than the generated schema; runtime shape is correct
        const response = await api.api_ApprovalRequests_list({
            queries: {
                content_type: contentTypeId,
                object_id: objectId!,
                ordering: "-requested_at",
                limit: 10,
            },
        }) as unknown as PaginatedResponse;
        return response.results;
    },
});

/**
 * Fetch the ApprovalRequests attached to any content object.
 *
 * Generalisation of `useDocumentApprovalRequest` — same query, but the
 * caller names the Django model (lowercase, e.g. 'processchangerequest',
 * 'processchangeorder', 'documents') instead of hardcoding documents.
 * Content-type id resolution goes through the shared mapping hook so the
 * model name → numeric id lookup is cached across the app.
 */
export function useApprovalRequestsFor(
    contentTypeModel: string,
    objectId: string | undefined,
) {
    const { getContentTypeId, isLoading: contentTypesLoading } = useContentTypeMapping();
    const contentTypeId = getContentTypeId(contentTypeModel);

    return useQuery({
        ...approvalRequestsForOptions(contentTypeId, objectId),
        enabled: objectId !== undefined && !!contentTypeId && !contentTypesLoading,
    });
}
