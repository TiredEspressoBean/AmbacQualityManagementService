import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateJobRoleInput = Schema<"JobRoleRequest">;
type CreateJobRoleResponse = Schema<"JobRole">;

export const useCreateJobRole = () => {
    const queryClient = useQueryClient();
    return useMutation<CreateJobRoleResponse, unknown, CreateJobRoleInput>({
        mutationFn: (data) =>
            api.api_JobRoles_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateJobRoleResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["job-roles"] });
        },
    });
};
