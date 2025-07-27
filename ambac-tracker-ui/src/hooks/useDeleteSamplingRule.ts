import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

export function useDeleteSamplingRule() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: number) =>
            api.api_Sampling_rules_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["sampling-rule", "delete"],
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["sampling-rule"] });
        },
    });
}
