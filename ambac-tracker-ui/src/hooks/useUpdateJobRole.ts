import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";
import { retrieveJobRoleOptions } from "@/hooks/useRetrieveJobRole";

type UpdateJobRoleInput = { id: string; data: Partial<Schema<"PatchedJobRoleRequest">> };

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const jobRolesKeyOptions = () => ({ queryKey: ["job-roles"] as const });

export const useUpdateJobRole = () => {
    const queryClient = useQueryClient();
    return useMutation<Schema<"JobRole">, unknown, UpdateJobRoleInput>({
        mutationFn: ({ id, data }) =>
            api.api_JobRoles_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<Schema<"JobRole">>,
        onSuccess: (_res, { id }) => {
            queryClient.invalidateQueries(jobRolesKeyOptions());
            queryClient.invalidateQueries(retrieveJobRoleOptions(id));
        },
    });
};
