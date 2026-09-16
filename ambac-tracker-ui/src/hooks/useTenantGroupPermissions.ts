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

// Invalidation-only helpers (not real queryOptions — no queryFn needed).
const tenantGroupKeyOptions = (groupId: string) => ({ queryKey: ["tenantGroup", groupId] as const });
const tenantGroupsKeyOptions = () => ({ queryKey: ["tenantGroups"] as const });

export function useAddTenantGroupPermissions(groupId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (permissions: string[]) =>

            // `{name: ""}` was padding for a schema that no longer applies: the
            // action declares {permissions} and zod was silently stripping the
            // name on every call.
            api.api_TenantGroups_permissions_create(
                { permissions },
                { params: { id: groupId } }
            ),
        onSuccess: () => {
            queryClient.invalidateQueries(tenantGroupKeyOptions(groupId));
            queryClient.invalidateQueries(tenantGroupPermissionsOptions(groupId));
            queryClient.invalidateQueries(tenantGroupsKeyOptions());
        },
    });
}

export function useSetTenantGroupPermissions(groupId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (permissions: string[]) =>

            api.api_TenantGroups_permissions_update(
                { permissions },
                { params: { id: groupId } }
            ),
        onSuccess: () => {
            queryClient.invalidateQueries(tenantGroupKeyOptions(groupId));
            queryClient.invalidateQueries(tenantGroupPermissionsOptions(groupId));
            queryClient.invalidateQueries(tenantGroupsKeyOptions());
        },
    });
}
