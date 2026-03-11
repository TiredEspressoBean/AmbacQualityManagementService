import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

type UserTenantsResponse = Awaited<ReturnType<typeof api.api_user_tenants_list>>;
export type UserTenant = UserTenantsResponse[number];

/**
 * Fetch all tenants the current user has access to.
 * Used for the tenant switcher in the sidebar.
 */
export function useUserTenants(
    options?: Omit<UseQueryOptions<UserTenantsResponse, Error>, "queryKey" | "queryFn">
) {
    return useQuery({
        queryKey: ["user", "tenants"],
        queryFn: () => api.api_user_tenants_list(),
        staleTime: 5 * 60 * 1000, // 5 minutes
        ...options,
    });
}
