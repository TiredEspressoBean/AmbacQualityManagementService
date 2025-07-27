import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

export function useDeleteRuleType() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: number) =>
            api.api_Sampling_rule_types_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["rule-type", "delete"],
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["rule-type"] });
        },
    });
}
