import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateJobRoleInput = { id: string; data: Partial<Schema<"PatchedJobRoleRequest">> };

export const useUpdateJobRole = () => {
    const queryClient = useQueryClient();
    return useMutation<Schema<"JobRole">, unknown, UpdateJobRoleInput>({
        mutationFn: ({ id, data }) =>
            api.api_JobRoles_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<Schema<"JobRole">>,
        onSuccess: (_res, { id }) => {
            queryClient.invalidateQueries({ queryKey: ["job-roles"] });
            queryClient.invalidateQueries({ queryKey: ["job-role", id] });
        },
    });
};
