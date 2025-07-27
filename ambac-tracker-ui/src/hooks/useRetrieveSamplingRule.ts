import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveSamplingRule(
    queries: Parameters<typeof api.api_Sampling_rules_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["sampling-rule", queries],
        queryFn: () => api.api_Sampling_rules_retrieve(queries),
        enabled: options?.enabled ?? true,
    });
}