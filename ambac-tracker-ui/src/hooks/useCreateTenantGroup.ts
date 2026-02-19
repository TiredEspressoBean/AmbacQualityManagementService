import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useCreateTenantGroup() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: { name: string; description?: string }) =>
            api.api_TenantGroups_create(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] });
        },
    });
}
