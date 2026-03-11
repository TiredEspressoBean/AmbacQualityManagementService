import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

// Extract queries type from Zodios endpoint
type CompaniesListQueries = Parameters<typeof api.api_Companies_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_Companies_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveCompanies(
  queries?: CompaniesListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_Companies_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["company", queries, config],
    queryFn: () => api.api_Companies_list(queries || config ? { queries, ...config } : undefined),
    ...options,
  });
}
