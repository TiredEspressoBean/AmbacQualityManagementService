import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveSamplingRules(
  queries?: Parameters<typeof api.api_Sampling_rules_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_Sampling_rules_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["sampling-rules", queries],
    queryFn: () => api.api_Sampling_rules_list(queries),
    ...options,
  });
}