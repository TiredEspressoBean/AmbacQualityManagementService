import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

export function useDeleteDocuments() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) =>
            api.api_Documents_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["documents", "delete"],
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["documents"] });
        },
    });
}
