import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

// Type for the query parameters (extracted from the Zodios endpoint)
type PartsListQueries = Parameters<typeof api.api_Parts_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_Parts_list>[0];

export function useRetrieveParts(
  queries?: PartsListQueries,
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_Parts_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["part", queries],
    queryFn: () => api.api_Parts_list(queries ? { queries } : undefined),
    ...options,
  });
}