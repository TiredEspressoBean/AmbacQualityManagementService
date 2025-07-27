import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveErrorTypes (queries: Parameters<typeof api.api_Error_types_list>[0]) {
    return useQuery({
        queryKey: ["error-types", queries],
        queryFn: () => api.api_Error_types_list(queries),
    });
};