import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useRetrieveIntegration(
    query: Parameters<typeof api.api_integrations_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["integration", query],
        queryFn: () => api.api_integrations_retrieve(query),
        enabled: options?.enabled ?? true,
    });
}
