import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

// Extract queries type from Zodios endpoint
type CapasListQueries = Parameters<typeof api.api_CAPAs_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_CAPAs_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useListCapas(
  queries?: CapasListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_CAPAs_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["capas", queries, config],
    queryFn: () => api.api_CAPAs_list(queries || config ? { queries, ...config } : undefined),
    ...options,
  });
}
