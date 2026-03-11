import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

type TenantSettingsResponse = Awaited<ReturnType<typeof api.api_tenant_settings_retrieve>>;

export function useTenantSettings(
    options?: Omit<UseQueryOptions<TenantSettingsResponse, Error>, "queryKey" | "queryFn">
) {
    return useQuery({
        queryKey: ["tenantSettings"],
        queryFn: () => api.api_tenant_settings_retrieve(),
        staleTime: 5 * 60 * 1000,
        ...options,
    });
}
