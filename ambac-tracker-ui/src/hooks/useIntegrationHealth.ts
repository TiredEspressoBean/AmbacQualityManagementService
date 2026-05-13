import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export const integrationHealthOptions = (query: Parameters<typeof api.api_integrations_health_retrieve>[0]) => queryOptions({
    queryKey: ["integration-health", query] as const,
    queryFn: () => api.api_integrations_health_retrieve(query),
});

export function useIntegrationHealth(query: Parameters<typeof api.api_integrations_health_retrieve>[0], options?: { enabled?: boolean }){
    return useQuery({ ...integrationHealthOptions(query), enabled: options?.enabled ?? true });
}
