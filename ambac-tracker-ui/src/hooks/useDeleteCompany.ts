import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

export function useDeleteCompany() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: number) =>
            api.api_Companies_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["Company", "delete"],
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["Company"] });
        },
    });
}
