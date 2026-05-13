import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

interface ScopedDocument {
    id: string;
    file_name: string;
    file_url: string | null;
    upload_date: string;
    is_image: boolean;
    classification: string;
}

interface ScopeResponse {
    documents?: ScopedDocument[];
    stats?: Record<string, number>;
}

/**
 * Fetch documents from a scoped subtree (e.g., all documents under an order).
 *
 * @param rootModel - The model name (e.g., 'orders', 'parttypes')
 * @param rootId - The ID of the root object
 * @param options - Optional filters like classification
 */
export const scopedDocumentsOptions = (
    rootModel: string,
    rootId: string | undefined,
    classification?: string,
) => queryOptions({
    queryKey: ["scope", "documents", rootModel, rootId, classification] as const,
    queryFn: async () => {
        // eslint-disable-next-line local/no-double-cast-via-unknown -- api_scope_list returns an untyped catch-all response; ScopeResponse matches runtime shape
        const data = await api.api_scope_list({
            queries: {
                root: `${rootModel}:${rootId}`,
                include: "documents",
                classification,
            },
        }) as unknown as ScopeResponse;
        return data.documents ?? [];
    },
});

export function useScopedDocuments(
    rootModel: string,
    rootId: string | undefined,
    options?: {
        classification?: string;
        enabled?: boolean;
    }
) {
    const { classification, enabled = true } = options ?? {};

    return useQuery({
        ...scopedDocumentsOptions(rootModel, rootId, classification),
        enabled: enabled && rootId !== undefined,
    });
}
