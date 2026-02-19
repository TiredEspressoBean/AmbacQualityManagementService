import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"
import { getCookie } from "@/lib/utils.ts";

export function useDeleteHeatMapAnnotation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) =>
            api.api_HeatMapAnnotation_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["heatMapAnnotation"] });
        },
    });
};
