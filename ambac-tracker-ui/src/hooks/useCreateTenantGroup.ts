import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateTenantGroupInput = Schema<"TenantGroupRequest">;
type CreateTenantGroupResponse = Schema<"TenantGroup">;

export function useCreateTenantGroup() {
    const queryClient = useQueryClient();

    return useMutation<CreateTenantGroupResponse, unknown, CreateTenantGroupInput>({
        mutationFn: (data) =>
            api.api_TenantGroups_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateTenantGroupResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] });
        },
    });
}
