import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

type ContentType = Schema<"ContentType">;

// Helper to normalize response (handles both array and paginated formats)
function normalizeContentTypes(data: ContentType[] | undefined): ContentType[] {
    return data || [];
}

export const contentTypesOptions = () => queryOptions({
    queryKey: ["content-types"] as const,
    queryFn: () => api.api_content_types_list({}),
});

export function useContentTypes() {
    return useQuery(contentTypesOptions());
}

export function useContentTypeMapping() {
    const { data: contentTypes, isLoading, error } = useContentTypes();
    const contentTypesList = normalizeContentTypes(contentTypes);

    const getContentTypeId = (modelName: string): number | undefined => {
        const contentType = contentTypesList.find(ct => ct.model === modelName);
        return contentType?.id;
    };

    return {
        getContentTypeId,
        contentTypes: contentTypesList,
        isLoading,
        error
    };
}
