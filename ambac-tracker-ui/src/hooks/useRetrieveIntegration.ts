import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export const retrieveIntegrationOptions = (query: Parameters<typeof api.api_integrations_retrieve>[0]) => queryOptions({
    queryKey: ["integration", query] as const,
    queryFn: () => api.api_integrations_retrieve(query),
});

export function useRetrieveIntegration(query: Parameters<typeof api.api_integrations_retrieve>[0], options?: { enabled?: boolean }){
    return useQuery({ ...retrieveIntegrationOptions(query), enabled: options?.enabled ?? true });
}
