import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type ErrorTypesListQueries = NonNullable<operations["api_Error_types_list"]["parameters"]["query"]>;
type ErrorTypesListResponse = components["schemas"]["PaginatedQualityErrorsListList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveErrorTypes(
  queries?: ErrorTypesListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<ErrorTypesListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<ErrorTypesListResponse, Error>({
    queryKey: ["error-type", queries, config],
    queryFn: () =>
      api.api_Error_types_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<ErrorTypesListResponse>,
    ...options,
  });
}
