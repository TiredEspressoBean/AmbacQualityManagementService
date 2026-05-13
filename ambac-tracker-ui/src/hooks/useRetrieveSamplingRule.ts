import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type SamplingRuleResponse = Schema<"SamplingRule">;

export const retrieveSamplingRuleOptions = (queries: Parameters<typeof api.api_Sampling_rules_retrieve>[0]) => queryOptions({
    queryKey: ["sampling-rule", queries] as const,
    queryFn: () => api.api_Sampling_rules_retrieve(queries) as Promise<SamplingRuleResponse>,
});

export function useRetrieveSamplingRule(queries: Parameters<typeof api.api_Sampling_rules_retrieve>[0], options?: { enabled?: boolean }){
    return useQuery({ ...retrieveSamplingRuleOptions(queries), enabled: options?.enabled ?? true });
}