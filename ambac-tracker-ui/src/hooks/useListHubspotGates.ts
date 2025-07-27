import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useListHubspotGates (queries: Parameters<typeof api.api_HubspotGates_list>[0]) {
    return useQuery({
        queryKey: ["hubspot_gates", queries],
        queryFn: () => api.api_HubspotGates_list(queries),
    });
};