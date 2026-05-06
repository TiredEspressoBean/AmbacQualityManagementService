import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type PartTypesListQueries = NonNullable<operations["api_PartTypes_list"]["parameters"]["query"]>;
type PartTypesListResponse = components["schemas"]["PaginatedPartTypesList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrievePartTypes(
  queries?: PartTypesListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<PartTypesListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<PartTypesListResponse, Error>({
    queryKey: ["part-type", queries, config],
    queryFn: () =>
      api.api_PartTypes_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<PartTypesListResponse>,
    ...options,
  });
}
