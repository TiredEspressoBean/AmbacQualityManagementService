import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type UpdateCapaTaskInput = Parameters<typeof api.api_CapaTasks_partial_update>[1];
type UpdateCapaTaskResponse = Awaited<ReturnType<typeof api.api_CapaTasks_partial_update>>;

export const useUpdateCapaTask = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateCapaTaskResponse, unknown, { id: string; data: UpdateCapaTaskInput }>({
        mutationFn: ({ id, data }) =>
            api.api_CapaTasks_partial_update({ id }, data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["capa-tasks"] });
            queryClient.invalidateQueries({ queryKey: ["capa"] });
        },
    });
};
