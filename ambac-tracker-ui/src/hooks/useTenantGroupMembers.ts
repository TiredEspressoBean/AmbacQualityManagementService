import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export type TenantGroupMember = {
    id: number;
    user_id: number;
    username: string;
    email: string;
    first_name?: string;
    last_name?: string;
    full_name?: string;
    is_active?: boolean;
};

export function useTenantGroupMembers(groupId: string | undefined, options?: { enabled?: boolean }) {
    return useQuery<TenantGroupMember[]>({
        queryKey: ["tenantGroup", groupId, "members"],
        queryFn: async () => {
            // Bypass zodios validation since schema says object but API returns array
            const response = await fetch(`/api/TenantGroups/${groupId}/members/`, {
                credentials: "include",
            });
            if (!response.ok) throw new Error("Failed to fetch members");
            return response.json();
        },
        enabled: (options?.enabled ?? true) && !!groupId,
    });
}

export function useAddTenantGroupMember(groupId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (userId: string) =>
            api.api_TenantGroups_members_create(
                { name: "", user_id: userId } as any,
                { params: { id: groupId } }
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId] });
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId, "members"] });
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] });
        },
    });
}

export function useRemoveTenantGroupMember(groupId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (userId: string) =>
            api.api_TenantGroups_members_destroy({ params: { id: groupId, user_id: userId } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId] });
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId, "members"] });
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] });
        },
    });
}
