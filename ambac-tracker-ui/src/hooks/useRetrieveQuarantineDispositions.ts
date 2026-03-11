import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

// Extract queries type from Zodios endpoint
type QuarantineDispositionsListQueries = Parameters<typeof api.api_QuarantineDispositions_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_QuarantineDispositions_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveQuarantineDispositions(
  queries?: QuarantineDispositionsListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_QuarantineDispositions_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["quarantine-disposition", queries, config],
    queryFn: () => api.api_QuarantineDispositions_list(queries || config ? { queries, ...config } : undefined),
    ...options,
  });
}
