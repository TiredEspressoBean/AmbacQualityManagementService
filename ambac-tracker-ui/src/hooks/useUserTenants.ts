import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

type UserTenantsResponse = Awaited<ReturnType<typeof api.api_user_tenants_list>>;
export type UserTenant = UserTenantsResponse[number];

/**
 * Fetch all tenants the current user has access to.
 * Used for the tenant switcher in the sidebar.
 */
export const userTenantsOptions = () => queryOptions({
    queryKey: ["user", "tenants"] as const,
    queryFn: () => api.api_user_tenants_list(),
});

export function useUserTenants(
    options?: Omit<ReturnType<typeof userTenantsOptions>, "queryKey" | "queryFn">
) {
    return useQuery({
        ...userTenantsOptions(),
        staleTime: 5 * 60 * 1000, // 5 minutes
        ...options,
    });
}
