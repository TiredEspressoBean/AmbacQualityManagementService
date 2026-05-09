import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type SamplingRuleResponse = Schema<"SamplingRule">;

export function useRetrieveSamplingRule(
    queries: Parameters<typeof api.api_Sampling_rules_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery<SamplingRuleResponse>({
        queryKey: ["sampling-rule", queries],
        queryFn: () => api.api_Sampling_rules_retrieve(queries) as Promise<SamplingRuleResponse>,
        enabled: options?.enabled ?? true,
    });
}