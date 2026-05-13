import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateTenantGroupInput = Schema<"PatchedTenantGroupRequest">;
type UpdateTenantGroupResponse = Schema<"TenantGroup">;

export function useUpdateTenantGroup(groupId: string) {
    const queryClient = useQueryClient();

    return useMutation<UpdateTenantGroupResponse, unknown, UpdateTenantGroupInput>({
        mutationFn: (data) =>
            api.api_TenantGroups_partial_update(data as never, {
                params: { id: groupId },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateTenantGroupResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenantGroup", groupId] });
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] });
        },
    });
}
