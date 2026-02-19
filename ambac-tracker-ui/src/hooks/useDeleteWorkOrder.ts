import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

export function useDeleteWorkOrder() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) =>
            api.api_WorkOrders_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["part-types", "delete"],
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["step"] });
        },
    });
}
