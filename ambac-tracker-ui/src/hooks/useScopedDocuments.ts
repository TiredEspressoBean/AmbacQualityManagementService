import { useQuery } from "@tanstack/react-query";
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
export function useScopedDocuments(
    rootModel: string,
    rootId: string | undefined,
    options?: {
        classification?: string;
        enabled?: boolean;
    }
) {
    const { classification, enabled = true } = options ?? {};

    return useQuery<ScopedDocument[]>({
        queryKey: ["scope", "documents", rootModel, rootId, classification],
        queryFn: async () => {
            const data = await api.api_scope_list({
                queries: {
                    root: `${rootModel}:${rootId}`,
                    include: "documents",
                    classification,
                },
            }) as ScopeResponse;
            return data.documents ?? [];
        },
        enabled: enabled && rootId !== undefined,
    });
}
