import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const qualityReportsKeyOptions = () => ({ queryKey: ["quality-reports"] as const });

export function useDeleteQualityReport() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) =>
            api.api_QualityReports_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["quality-reports", "delete"],
        onSuccess: () => {
            queryClient.invalidateQueries(qualityReportsKeyOptions());
        },
    });
}
