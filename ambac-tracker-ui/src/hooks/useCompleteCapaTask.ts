import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CompleteCapaTaskInput = Parameters<typeof api.api_CapaTasks_complete_create>[1];
type CompleteCapaTaskResponse = Awaited<ReturnType<typeof api.api_CapaTasks_complete_create>>;

export const useCompleteCapaTask = () => {
    const queryClient = useQueryClient();

    return useMutation<CompleteCapaTaskResponse, unknown, { id: string; data: CompleteCapaTaskInput }>({
        mutationFn: ({ id, data }) =>
            api.api_CapaTasks_complete_create({ id }, data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["capa-tasks"] });
            queryClient.invalidateQueries({ queryKey: ["capa"] });
        },
    });
};
