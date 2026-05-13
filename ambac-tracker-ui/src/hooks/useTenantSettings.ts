import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export const tenantSettingsOptions = () => queryOptions({
    queryKey: ["tenantSettings"] as const,
    queryFn: () => api.api_tenant_settings_retrieve(),
});

export function useTenantSettings(
    options?: Omit<ReturnType<typeof tenantSettingsOptions>, "queryKey" | "queryFn">
) {
    return useQuery({
        ...tenantSettingsOptions(),
        staleTime: 5 * 60 * 1000,
        ...options,
    });
}
