import { useQuery } from "@tanstack/react-query";
import { api, type ContentType } from "@/lib/api/generated";

// Helper to normalize response (handles both array and paginated formats)
function normalizeContentTypes(data: ContentType[] | undefined): ContentType[] {
    return data || [];
}

export function useContentTypes() {
    return useQuery<ContentType[], Error>({
        queryKey: ["content-types"],
        queryFn: () => api.api_content_types_list({}),
    });
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