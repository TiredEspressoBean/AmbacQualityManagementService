import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

export function useDeleteErrorType() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) =>
            api.api_Error_types_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["error-types", "delete"],
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["error-types"] });
        },
    });
}
