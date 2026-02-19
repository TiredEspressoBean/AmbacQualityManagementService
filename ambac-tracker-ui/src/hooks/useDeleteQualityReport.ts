import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

export function useDeleteQualityReport() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) =>
            api.api_ErrorReports_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["quality-reports", "delete"],
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["quality-reports"] });
        },
    });
}
