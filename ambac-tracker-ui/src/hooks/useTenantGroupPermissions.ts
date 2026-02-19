import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useTenantGroupPermissions(groupId: string | undefined, options?: { enabled?: boolean }) {
    return useQuery({
        queryKey: ["tenantGroup", groupId, "permissions"],
        queryFn: () => api.api_TenantGroups_permissions_retrieve({ params: { id: groupId! } }),
        enabled: (options?.enabled ?? true) && !!groupId,
    });
}

export function useAddTenantGroupPermissions(groupId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (permissions: string[]) =>
            api.api_TenantGroups_permissions_create(
                { name: "", permissions } as any,
                { params: { id: groupId } }
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId] });
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId, "permissions"] });
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] });
        },
    });
}

export function useSetTenantGroupPermissions(groupId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (permissions: string[]) =>
            api.api_TenantGroups_permissions_update(
                { name: "", permissions } as any,
                { params: { id: groupId } }
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId] });
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId, "permissions"] });
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] });
        },
    });
}
