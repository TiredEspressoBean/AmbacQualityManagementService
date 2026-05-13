import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

type EffectivePermissionsResponse = Awaited<ReturnType<typeof api.api_users_me_effective_permissions_retrieve>>;

export type { EffectivePermissionsResponse };

export const myPermissionsOptions = () => queryOptions({
    queryKey: ["myPermissions"] as const,
    queryFn: () => api.api_users_me_effective_permissions_retrieve(),
});

export function useMyPermissions(
    options?: Omit<ReturnType<typeof myPermissionsOptions>, "queryKey" | "queryFn">
) {
    return useQuery({
        ...myPermissionsOptions(),
        staleTime: 5 * 60 * 1000, // Cache for 5 minutes
        retry: 1,
        ...options,
    });
}

/**
 * Helper hook that returns a Set for easy permission checking
 */
export function usePermissionSet() {
    const { data, isLoading, isError } = useMyPermissions();

    const permissions = new Set(data?.effective_permissions ?? []);

    return {
        permissions,
        isLoading,
        isError,
        has: (perm: string) => permissions.has(perm),
        hasAny: (...perms: string[]) => perms.some(p => permissions.has(p)),
        hasAll: (...perms: string[]) => perms.every(p => permissions.has(p)),
    };
}
