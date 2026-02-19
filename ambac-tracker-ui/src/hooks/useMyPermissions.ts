import { useQuery } from "@tanstack/react-query";

export type EffectivePermissionsResponse = {
    user_id: string;
    user_email: string;
    groups: {
        group_id: string;
        group_name: string;
        facility: string | null;
        company: string | null;
        permission_count: number;
    }[];
    effective_permissions: string[];
    total_count: number;
};

export function useMyPermissions(options?: { enabled?: boolean }) {
    return useQuery<EffectivePermissionsResponse>({
        queryKey: ["myPermissions"],
        queryFn: async () => {
            const response = await fetch("/api/users/me/effective-permissions/", {
                credentials: "include",
            });
            if (!response.ok) {
                throw new Error("Failed to fetch permissions");
            }
            return response.json();
        },
        staleTime: 5 * 60 * 1000, // Cache for 5 minutes
        retry: 1,
        enabled: options?.enabled ?? true,
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
