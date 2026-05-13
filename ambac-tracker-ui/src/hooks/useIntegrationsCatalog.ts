import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export const integrationsCatalogOptions = () => queryOptions({
    queryKey: ["integrations-catalog"] as const,
    queryFn: () => api.api_integrations_catalog_list(),
});

export function useIntegrationsCatalog(options?: { enabled?: boolean }) {
    return useQuery({ ...integrationsCatalogOptions(), enabled: options?.enabled ?? true });
}
