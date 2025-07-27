import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveStepWithSamplingRules(
    queries: Parameters<typeof api.api_Steps_resolved_rules_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["step-and-rules", queries],
        queryFn: () => api.api_Steps_resolved_rules_retrieve(queries),
        enabled: options?.enabled ?? true,
    });
}