import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveCompany(
    query: Parameters<typeof api.api_Companies_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["company", query],
        queryFn: () => api.api_Companies_retrieve(query),
        enabled: options?.enabled ?? true,
    });
}