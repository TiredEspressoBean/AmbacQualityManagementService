import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec.
type QuarantineDispositionsListQueries = NonNullable<operations["api_QuarantineDispositions_list"]["parameters"]["query"]>;
type QuarantineDispositionsListResponse = components["schemas"]["PaginatedQuarantineDispositionList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const retrieveQuarantineDispositionsOptions = (queries?: QuarantineDispositionsListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["quarantine-disposition", queries, config] as const,
  queryFn: () =>
    api.api_QuarantineDispositions_list(
      (queries || config ? { queries, ...config } : undefined) as never,
    ) as Promise<QuarantineDispositionsListResponse>,
});

export function useRetrieveQuarantineDispositions(
  queries?: QuarantineDispositionsListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof retrieveQuarantineDispositionsOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...retrieveQuarantineDispositionsOptions(queries, config),
    ...options,
  });
}
