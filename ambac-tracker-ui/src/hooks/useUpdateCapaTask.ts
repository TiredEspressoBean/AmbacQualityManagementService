import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateCapaTaskInput = Schema<"PatchedCapaTasksRequest">;
type UpdateCapaTaskResponse = Schema<"CapaTasks">;

export const useUpdateCapaTask = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateCapaTaskResponse, unknown, { id: string; data: UpdateCapaTaskInput }>({
        mutationFn: ({ id, data }) =>
            api.api_CapaTasks_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateCapaTaskResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["capa-tasks"] });
            queryClient.invalidateQueries({ queryKey: ["capa"] });
        },
    });
};
