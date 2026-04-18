import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useIntegrationsCatalog(
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["integrations-catalog"],
        queryFn: () => api.api_integrations_catalog_list(),
        enabled: options?.enabled ?? true,
    });
}
