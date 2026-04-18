import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useIntegrationHealth(
    query: Parameters<typeof api.api_integrations_health_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["integration-health", query],
        queryFn: () => api.api_integrations_health_retrieve(query),
        enabled: options?.enabled ?? true,
    });
}
