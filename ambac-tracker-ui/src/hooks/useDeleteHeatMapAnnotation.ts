import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"
import { getCookie } from "@/lib/utils.ts";

export function useDeleteHeatMapAnnotation() {
    const queryClient = useQueryClient();

    return useMutation({
        // The annotator toasts the server's reason itself (a finished report's
        // annotation is refused to non-quality roles).
        meta: { suppressGlobalError: true },
        mutationFn: (id: string) =>
            api.api_HeatMapAnnotation_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "heatMapAnnotation" });
        },
    });
};
