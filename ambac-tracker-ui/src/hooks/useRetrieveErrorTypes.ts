import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type ErrorTypesListQueries = NonNullable<operations["api_Error_types_list"]["parameters"]["query"]>;
type ErrorTypesListResponse = components["schemas"]["PaginatedQualityErrorsListList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const errorTypesOptions = (queries?: ErrorTypesListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["error-type", queries, config] as const,
    queryFn: () =>
      api.api_Error_types_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<ErrorTypesListResponse>,
  });

export const errorTypesMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "ErrorTypes", "Error-types"] as const,
    queryFn: () => api.api_Error_types_metadata_retrieve(),
  });

export function useRetrieveErrorTypes(
  queries?: ErrorTypesListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof errorTypesOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...errorTypesOptions(queries, config),
    ...options,
  });
}
