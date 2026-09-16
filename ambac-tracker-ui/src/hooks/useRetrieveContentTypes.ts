import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

// Extract queries type from Zodios endpoint
// The `extends { queries?: infer Q }` form this used fell through -- the
// param is optional, so the check failed and Q resolved to the whole config
// object rather than the query shape. Indexing it directly is what was
// meant, and it is what makes the call typecheck without a cast.
type ContentTypesListQueries = NonNullable<Parameters<typeof api.api_content_types_list>[0]>["queries"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const retrieveContentTypesOptions = (queries?: ContentTypesListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["contentTypes", queries, config] as const,
  queryFn: () => api.api_content_types_list({ queries, ...config }),
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
