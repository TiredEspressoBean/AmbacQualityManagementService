import { useQuery, queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

// Shape returned by /api/TenantGroups/:id/members/ — see backend's UserRoleSerializer
// in Tracker/viewsets/tenant.py. The endpoint returns UserRole rows (group memberships),
// NOT bare users. The earlier shape declared here (username/email/user_id) was a
// fabrication that never matched the API response, hiding the real schema from consumers.
export type TenantGroupMember = {
    id: string;
    user: number;
    user_email: string;
    user_name: string;
    group: string;
    group_name: string;
    company?: string | null;
    company_name?: string | null;
    facility?: string | null;
    facility_name?: string | null;
    granted_at: string;
    granted_by?: number | null;
    granted_by_name?: string | null;
};

export const tenantGroupMembersOptions = (groupId: string | undefined) => queryOptions({
    queryKey: ["tenantGroup", groupId, "members"] as const,
    queryFn: async () => {
        // eslint-disable-next-line no-restricted-syntax -- OpenAPI schema is wrong: schema says TenantGroup object but API returns array of members. Fix backend schema to use typed client.
        const response = await fetch(`/api/TenantGroups/${groupId}/members/`, {
            credentials: "include",
        });
        if (!response.ok) throw new Error("Failed to fetch members");
        return response.json() as Promise<TenantGroupMember[]>;
    },
});

export function useTenantGroupMembers(groupId: string | undefined, options?: { enabled?: boolean }) {
    return useQuery({
        ...tenantGroupMembersOptions(groupId),
        enabled: (options?.enabled ?? true) && !!groupId,
    });
}

export function useAddTenantGroupMember(groupId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (userId: string) =>
            api.api_TenantGroups_members_create(
                // eslint-disable-next-line local/no-as-any -- TenantGroupMember create body doesn't match generated schema; only user_id is needed at runtime
                { name: "", user_id: userId } as any,
                { params: { id: groupId } }
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId] as const });
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId, "members"] as const });
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] as const });
        },
    });
}

export function useRemoveTenantGroupMember(groupId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (userId: string) =>
            api.api_TenantGroups_members_destroy(undefined, { params: { id: groupId, user_id: userId } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId] as const });
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId, "members"] as const });
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] as const });
        },
    });
}
