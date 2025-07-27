import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

export function useDeleteStep() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: number) =>
            api.api_Steps_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["part-types", "delete"],
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["step"] });
        },
    });
}
