import { useQuery, queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export const tenantGroupPermissionsOptions = (groupId: string | undefined) => queryOptions({
    queryKey: ["tenantGroup", groupId, "permissions"] as const,
    queryFn: () => api.api_TenantGroups_permissions_retrieve({ params: { id: groupId! } }),
});

export function useTenantGroupPermissions(groupId: string | undefined, options?: { enabled?: boolean }) {
    return useQuery({
        ...tenantGroupPermissionsOptions(groupId),
        enabled: (options?.enabled ?? true) && !!groupId,
    });
}

export function useAddTenantGroupPermissions(groupId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (permissions: string[]) =>

            api.api_TenantGroups_permissions_create(
                { name: "", permissions } as never,
                { params: { id: groupId } }
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId] as const });
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId, "permissions"] as const });
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] as const });
        },
    });
}

export function useSetTenantGroupPermissions(groupId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (permissions: string[]) =>

            api.api_TenantGroups_permissions_update(
                { name: "", permissions } as never,
                { params: { id: groupId } }
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId] as const });
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId, "permissions"] as const });
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] as const });
        },
    });
}
