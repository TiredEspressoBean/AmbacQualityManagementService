import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveContentTypes (queries: Parameters<typeof api.api_content_types_list>[0]) {
    return useQuery({
        queryKey: ["content-types", queries],
        queryFn: () => api.api_content_types_list(queries),
    });
};