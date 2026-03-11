import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

// Extract queries type from Zodios endpoint
type ContentTypesListQueries = Parameters<typeof api.api_content_types_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_content_types_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveContentTypes(
  queries?: ContentTypesListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_content_types_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["contentTypes", queries, config],
    queryFn: () => api.api_content_types_list(queries || config ? { queries, ...config } : undefined),
    ...options,
  });
}
