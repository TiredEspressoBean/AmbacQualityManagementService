import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

export const useDeleteCapaTask = () => {
    const queryClient = useQueryClient();

    return useMutation<void, unknown, number>({
        mutationFn: (id) =>
            api.api_CapaTasks_destroy({ id }, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["capa-tasks"] });
            queryClient.invalidateQueries({ queryKey: ["capa"] });
        },
    });
};
