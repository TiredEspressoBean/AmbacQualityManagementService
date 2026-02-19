import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useTenantGroups(
    params?: Parameters<typeof api.api_TenantGroups_list>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["tenantGroups", params],
        queryFn: () => api.api_TenantGroups_list(params),
        enabled: options?.enabled ?? true,
    });
}
