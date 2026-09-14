import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const stepKeyOptions = () => ({ queryKey: ["step"] as const });

export function useDeleteStep() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) =>
            api.api_Steps_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["part-types", "delete"],
        onSuccess: () => {
            queryClient.invalidateQueries(stepKeyOptions());
        },
    });
}
