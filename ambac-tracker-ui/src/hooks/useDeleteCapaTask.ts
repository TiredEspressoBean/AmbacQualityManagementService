import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

export const useDeleteCapaTask = () => {
    const queryClient = useQueryClient();

    return useMutation<void, unknown, string>({
        mutationFn: (id) =>
            api.api_CapaTasks_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "capa-tasks" });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "capa" });
        },
    });
};
