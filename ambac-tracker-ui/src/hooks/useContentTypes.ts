import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useContentTypes() {
    return useQuery({
        queryKey: ["content-types"],
        queryFn: () => api.api_content_types_list({ queries: { limit: 100 } }),
        staleTime: 5 * 60 * 1000, // Content types rarely change, cache for 5 minutes
    });
}

export function useContentTypeMapping() {
    const { data: contentTypes, isLoading, error } = useContentTypes();

    const getContentTypeId = (modelName: string): number | undefined => {
        if (!contentTypes?.results) return undefined;
        const contentType = contentTypes.results.find(ct => ct.model === modelName);
        return contentType?.id;
    };

    return {
        getContentTypeId,
        contentTypes: contentTypes?.results || [],
        isLoading,
        error
    };
}