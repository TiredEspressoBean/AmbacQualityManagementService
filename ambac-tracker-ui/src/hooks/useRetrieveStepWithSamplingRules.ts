import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export const retrieveStepWithSamplingRulesOptions = (queries: Parameters<typeof api.api_Steps_resolved_rules_retrieve>[0]) => queryOptions({
    queryKey: ["step-and-rules", queries] as const,
    queryFn: () => api.api_Steps_resolved_rules_retrieve(queries),
});

export function useRetrieveStepWithSamplingRules(queries: Parameters<typeof api.api_Steps_resolved_rules_retrieve>[0], options?: { enabled?: boolean }){
    return useQuery({ ...retrieveStepWithSamplingRulesOptions(queries), enabled: options?.enabled ?? true });
}