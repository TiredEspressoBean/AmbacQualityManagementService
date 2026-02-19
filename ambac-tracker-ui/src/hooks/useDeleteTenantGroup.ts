import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useDeleteTenantGroup() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (groupId: string) =>
            api.api_TenantGroups_destroy({ params: { id: groupId } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] });
        },
    });
}
