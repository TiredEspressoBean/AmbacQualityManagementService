import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec.
type QuarantineDispositionsListQueries = NonNullable<operations["api_QuarantineDispositions_list"]["parameters"]["query"]>;
type QuarantineDispositionsListResponse = components["schemas"]["PaginatedQuarantineDispositionList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveQuarantineDispositions(
  queries?: QuarantineDispositionsListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<QuarantineDispositionsListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<QuarantineDispositionsListResponse, Error>({
    queryKey: ["quarantine-disposition", queries, config],
    queryFn: () =>
      api.api_QuarantineDispositions_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<QuarantineDispositionsListResponse>,
    ...options,
  });
}
