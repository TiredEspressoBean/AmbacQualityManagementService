import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useUpdateTenantGroup(groupId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: { name?: string; description?: string }) =>
            api.api_TenantGroups_partial_update(data, { params: { id: groupId } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId] });
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] });
        },
    });
}
