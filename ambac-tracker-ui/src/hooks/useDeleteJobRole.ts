import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const jobRolesKeyOptions = () => ({ queryKey: ["job-roles"] as const });

export const useDeleteJobRole = () => {
    const queryClient = useQueryClient();
    return useMutation<void, unknown, { id: string }>({
        mutationFn: ({ id }) =>
            api.api_JobRoles_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries(jobRolesKeyOptions());
        },
    });
};
