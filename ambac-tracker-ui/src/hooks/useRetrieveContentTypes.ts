import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

// Extract queries type from Zodios endpoint
type ContentTypesListQueries = Parameters<typeof api.api_content_types_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_content_types_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const retrieveContentTypesOptions = (queries?: ContentTypesListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["contentTypes", queries, config] as const,
  queryFn: () => api.api_content_types_list(
    (queries || config ? { queries, ...config } : undefined) as never,
  ),
});

export function useRetrieveContentTypes(
  queries?: ContentTypesListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof retrieveContentTypesOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...retrieveContentTypesOptions(queries, config),
    ...options,
  });
}
