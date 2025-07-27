import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveCompanies (queries: Parameters<typeof api.api_Companies_list>[0]) {
    return useQuery({
        queryKey: ["company", queries],
        queryFn: () => api.api_Companies_list(queries),
    });
};